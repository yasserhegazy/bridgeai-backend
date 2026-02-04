"""
Team Service Module.
Handles all business logic for team operations including CRUD, member management, and invitations.
Following architectural rules: stateless, no direct db.session access, uses repositories.
"""
from typing import List, Optional, Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.team import Team, TeamMember, TeamRole, TeamStatus
from app.models.user import User
from app.models.project import Project
from app.models.invitation import Invitation
from app.services.permission_service import PermissionService
from app.services import notification_service
from app.repositories import (
    TeamRepository,
    TeamMemberRepository,
    UserRepository,
    ProjectRepository,
    InvitationRepository,
)
from app.utils.invitation import (
    build_invitation_link,
    create_invitation,
    send_invitation_email_to_console,
)


class TeamService:
    """Service for managing team operations."""

    @staticmethod
    def create_team(
        db: Session, name: str, description: str, current_user: User
    ) -> Team:
        """Create a new team. The creator automatically becomes the owner."""
        team_repo = TeamRepository(db)
        team_member_repo = TeamMemberRepository(db)
        
        # Check if team name already exists for this user
        existing_team = team_repo.get_by_name_and_creator(name, current_user.id)
        if existing_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have a team with this name",
            )

        # Create the team
        team = team_repo.create(
            Team(name=name, description=description, created_by=current_user.id)
        )

        # Add creator as owner
        team_member_repo.create(
            TeamMember(
                team_id=team.id, user_id=current_user.id, role=TeamRole.owner
            )
        )

        # Return team with members
        return team_repo.get_with_members(team.id)

    @staticmethod
    def list_teams(
        db: Session,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[TeamStatus] = None,
    ) -> List[Dict[str, Any]]:
        """List teams. Users can see teams they are members of."""
        team_repo = TeamRepository(db)
        team_member_repo = TeamMemberRepository(db)
        
        teams = team_repo.get_user_teams(current_user.id, skip, limit, status_filter)

        # Add member count to each team
        result = []
        for team in teams:
            member_count = team_member_repo.get_active_member_count(team.id)
            team_dict = {
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "status": team.status,
                "created_by": team.created_by,
                "created_at": team.created_at,
                "member_count": member_count,
            }
            result.append(team_dict)

        return result

    @staticmethod
    def get_team(db: Session, team_id: int, current_user: User) -> Team:
        """Get team details. Only team members can view team details."""
        team_member_repo = TeamMemberRepository(db)
        # Check if user is a member of the team
        team_member = team_member_repo.get_by_team_and_user(team_id, current_user.id)
        if not team_member or not team_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You are not a member of this team.",
            )

        team_repo = TeamRepository(db)
        team = team_repo.get_with_members(team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
            )

        return team

    @staticmethod
    def update_team(
        db: Session,
        team_id: int,
        current_user: User,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status_update: Optional[TeamStatus] = None,
    ) -> Team:
        """Update team. Only owners and admins can update teams."""
        # Check if user has permission (owner or admin)
        PermissionService.verify_team_admin(db, team_id, current_user.id)

        team = PermissionService.get_team_or_404(db, team_id)

        # Check if user is trying to update name to one that already exists for them
        if name and name != team.name:
            team_repo = TeamRepository(db)
            existing_team = team_repo.get_by_name_and_creator_excluding(
                name, current_user.id, team_id
            )
            if existing_team:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You already have another team with this name",
                )

        # Update team fields
        if name is not None:
            team.name = name
        if description is not None:
            team.description = description
        if status_update is not None:
            team.status = status_update

        team_repo = TeamRepository(db)
        updated_team = team_repo.update(team)

        # Return team with members
        return team_repo.get_with_members(updated_team.id)

    @staticmethod
    def delete_team(db: Session, team_id: int, current_user: User) -> None:
        """Delete a team. Only owners can delete teams."""
        # Ensure current user is the owner
        PermissionService.verify_team_owner(db, team_id, current_user.id)

        team_repo = TeamRepository(db)
        team = team_repo.get_by_id(team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
            )

        # Prevent deletion when projects exist
        project_count = team_repo.count_projects(team_id)
        if project_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot delete team with {project_count} project(s). "
                    "Please delete or move all projects first, or archive the team instead."
                ),
            )

        team_repo.delete(team)
        db.commit()

    @staticmethod
    def add_member(
        db: Session, team_id: int, user_id: int, role: TeamRole, current_user: User
    ) -> TeamMember:
        """Add a member to the team. Only owners and admins can add members."""
        # Check if current user has permission
        PermissionService.verify_team_admin(db, team_id, current_user.id)

        # Check if team exists
        team = PermissionService.get_team_or_404(db, team_id)

        # Check if user exists
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Check if user is already a member
        team_member_repo = TeamMemberRepository(db)
        existing_member = team_member_repo.get_by_team_and_user(team_id, user_id)

        if existing_member:
            if existing_member.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already a member of this team",
                )
            else:
                # Reactivate the member
                existing_member.is_active = True
                existing_member.role = role
                return team_member_repo.update(existing_member)

        # Add new member
        new_member = team_member_repo.create(
            TeamMember(team_id=team_id, user_id=user_id, role=role)
        )

        return new_member

    @staticmethod
    def list_members(
        db: Session, team_id: int, current_user: User, include_inactive: bool = False
    ) -> List[TeamMember]:
        """List team members. Only team members can view the member list."""
        team_member_repo = TeamMemberRepository(db)
        # Check if user is a member of the team
        team_member = team_member_repo.get_by_team_and_user(team_id, current_user.id)
        if not team_member or not team_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You are not a member of this team.",
            )

        members = team_member_repo.get_team_members_with_users(
            team_id, include_inactive
        )
        return members

    @staticmethod
    def update_member(
        db: Session,
        team_id: int,
        member_id: int,
        current_user: User,
        role: Optional[TeamRole] = None,
        is_active: Optional[bool] = None,
    ) -> TeamMember:
        """Update team member role or status. Only owners and admins can update members."""
        # Check if current user has permission
        current_member = PermissionService.verify_team_admin(db, team_id, current_user.id)

        # Get the member to update
        team_member_repo = TeamMemberRepository(db)
        member = team_member_repo.get_by_id(member_id)
        if not member or member.team_id != team_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found"
            )

        # Prevent demoting the last owner
        if member.role == TeamRole.owner and role and role != TeamRole.owner:
            owner_count = team_member_repo.count_active_owners(team_id)

            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the last owner of the team",
                )

        # Update member
        if role is not None:
            member.role = role
        if is_active is not None:
            member.is_active = is_active

        return team_member_repo.update(member)

    @staticmethod
    def remove_member(
        db: Session, team_id: int, member_id: int, current_user: User
    ) -> Dict[str, str]:
        """Remove a member from the team. Only owners and admins can remove members."""
        # Check if current user has permission
        current_member = PermissionService.verify_team_admin(db, team_id, current_user.id)

        # Get the member to remove
        team_member_repo = TeamMemberRepository(db)
        member = team_member_repo.get_by_id(member_id)
        if not member or member.team_id != team_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found"
            )

        # Prevent removing the last owner
        if member.role == TeamRole.owner:
            owner_count = team_member_repo.count_active_owners(team_id)

            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last owner of the team",
                )

        # Mark member as inactive instead of deleting
        member.is_active = False
        team_member_repo.update(member)

        return {"message": "Team member removed successfully"}

    @staticmethod
    def list_team_projects(
        db: Session, team_id: int, current_user: User
    ) -> List[Dict[str, Any]]:
        """List projects belonging to a team. Only team members can view projects."""
        team_member_repo = TeamMemberRepository(db)
        # Check if user is a member of the team
        team_member = team_member_repo.get_by_team_and_user(team_id, current_user.id)
        if not team_member or not team_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You are not a member of this team.",
            )

        # Get all projects for this team
        project_repo = ProjectRepository(db)
        projects = project_repo.get_by_team(team_id)

        return [
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "created_by": project.created_by,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
            }
            for project in projects
        ]

    @staticmethod
    def invite_member(
        db: Session, team_id: int, email: str, role: str, current_user: User
    ) -> Dict[str, Any]:
        """Invite a user to join the team by email. Only owners and admins can invite."""
        # Check if current user has permission to invite
        PermissionService.verify_team_admin(db, team_id, current_user.id)

        # Check if team exists
        team = PermissionService.get_team_or_404(db, team_id)

        # Check if user is already a member
        user_repo = UserRepository(db)
        existing_user = user_repo.get_by_email(email)
        if existing_user:
            team_member_repo = TeamMemberRepository(db)
            existing_member = team_member_repo.get_by_team_and_user(
                team_id, existing_user.id
            )
            if existing_member and existing_member.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already a member of this team",
                )

        # Check if there's already a pending invitation for this email
        invitation_repo = InvitationRepository(db)
        existing_invitation = invitation_repo.get_by_team_and_email(
            team_id, email, status="pending"
        )
        if existing_invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An invitation has already been sent to this email",
            )

        # Create invitation
        invitation = create_invitation(
            db=db,
            team_id=team_id,
            email=email,
            role=role,
            invited_by_user_id=current_user.id,
        )

        # Build invitation link
        invite_link = build_invitation_link(invitation.token)

        # Send invitation email via SMTP
        send_invitation_email_to_console(
            email=email,
            invite_link=invite_link,
            team_name=team.name,
            inviter_name=(
                current_user.full_name
                if hasattr(current_user, "full_name")
                else current_user.username
            ),
        )

        # If the invited email belongs to an existing user, create an in-app notification
        user_repo = UserRepository(db)
        invited_user = user_repo.get_by_email(email)
        if invited_user:
            notification_service.notify_team_invitation(
                db=db,
                team_id=team_id,
                team_name=team.name,
                inviter_name=current_user.full_name,
                role=role,
                invited_user_id=invited_user.id,
                commit=True,
            )

        return {
            "invite_link": invite_link,
            "status": invitation.status,
            "invitation": invitation,
        }

    @staticmethod
    def list_invitations(
        db: Session, team_id: int, current_user: User, include_expired: bool = False
    ) -> List[Invitation]:
        """
        List all invitations for a team.
        Only team owners and admins can view invitations.
        """
        # Check if current user has permission (owner or admin)
        PermissionService.verify_team_admin(db, team_id, current_user.id)

        # Check if team exists
        team_repo = TeamRepository(db)
        team = team_repo.get_by_id(team_id)
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
            )

        # Query invitations
        invitation_repo = InvitationRepository(db)
        if include_expired:
            invitations = invitation_repo.get_team_invitations(team_id)
        else:
            invitations = invitation_repo.get_team_invitations(team_id, status="pending")

        # Sort by created_at descending
        invitations.sort(key=lambda x: x.created_at, reverse=True)

        # Update expired invitations
        for invitation in invitations:
            if invitation.status == "pending" and invitation.is_expired():
                invitation.status = "expired"

        db.commit()

        return invitations

    @staticmethod
    def cancel_invitation(
        db: Session, team_id: int, invitation_id: int, current_user: User
    ) -> Dict[str, str]:
        """
        Cancel a pending invitation.
        Only team owners and admins can cancel invitations.
        """
        # Check if current user has permission
        PermissionService.verify_team_admin(db, team_id, current_user.id)

        # Get the invitation
        invitation_repo = InvitationRepository(db)
        invitation = invitation_repo.get_by_id(invitation_id)
        if not invitation or invitation.team_id != team_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
            )

        if invitation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only cancel pending invitations",
            )

        # Mark as cancelled
        invitation.status = "cancelled"
        invitation_repo.update(invitation)

        return {"message": "Invitation cancelled successfully"}
