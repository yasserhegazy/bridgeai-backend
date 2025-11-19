from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from app.db.session import get_db
from app.schemas.team import (
    TeamCreate, TeamUpdate, TeamOut, TeamListOut,
    TeamMemberCreate, TeamMemberUpdate, TeamMemberDetailOut
)
from app.models.team import Team, TeamMember, TeamRole, TeamStatus
from app.models.user import User
from app.models.project import Project
from app.models.invitation import Invitation
from app.core.security import get_current_user
from app.schemas.invitation import InvitationCreate, InvitationResponse, InvitationOut
from app.utils.invitation import create_invitation, send_invitation_email_to_console, build_invitation_link


router = APIRouter()


# Team CRUD endpoints
@router.post("/", response_model=TeamOut)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new team. The creator automatically becomes the owner."""
    # Check if team name already exists for this user
    existing_team = db.query(Team).filter(
        Team.name == payload.name,
        Team.created_by == current_user.id
    ).first()
    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a team with this name"
        )
    
    # Create the team
    team = Team(
        name=payload.name,
        description=payload.description,
        created_by=current_user.id
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # Add creator as owner
    team_member = TeamMember(
        team_id=team.id,
        user_id=current_user.id,
        role=TeamRole.owner
    )
    db.add(team_member)
    db.commit()
    
    # Return team with members
    team_with_members = db.query(Team).options(joinedload(Team.members)).filter(Team.id == team.id).first()
    return team_with_members


@router.get("/", response_model=List[TeamListOut])
def list_teams(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[TeamStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List teams. Users can see teams they are members of."""
    query = db.query(Team).join(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    )
    
    if status_filter:
        query = query.filter(Team.status == status_filter)
    
    teams = query.offset(skip).limit(limit).all()
    
    # Add member count to each team
    result = []
    for team in teams:
        member_count = db.query(func.count(TeamMember.id)).filter(
            TeamMember.team_id == team.id,
            TeamMember.is_active == True
        ).scalar()
        
        team_dict = {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "status": team.status,
            "created_by": team.created_by,
            "created_at": team.created_at,
            "member_count": member_count
        }
        result.append(team_dict)
    
    return result


@router.get("/{team_id}", response_model=TeamOut)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get team details. Only team members can view team details."""
    # Check if user is a member of the team
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this team."
        )
    
    team = db.query(Team).options(joinedload(Team.members)).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    return team


@router.put("/{team_id}", response_model=TeamOut)
def update_team(
    team_id: int,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update team. Only owners and admins can update teams."""
    # Check if user has permission (owner or admin)
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True,
        TeamMember.role.in_([TeamRole.owner, TeamRole.admin])
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only team owners and admins can update teams."
        )
    
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    # Validate that only allowed fields are being updated
    update_data = payload.dict(exclude_unset=True)
    
    # Check if user is trying to update name to one that already exists for them
    if "name" in update_data and update_data["name"] != team.name:
        existing_team = db.query(Team).filter(
            Team.name == update_data["name"],
            Team.created_by == current_user.id,
            Team.id != team_id  # Exclude current team
        ).first()
        if existing_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have another team with this name"
            )
    
    # Update team fields
    for field, value in update_data.items():
        setattr(team, field, value)
    
    db.commit()
    db.refresh(team)
    
    # Return team with members
    team_with_members = db.query(Team).options(joinedload(Team.members)).filter(Team.id == team.id).first()
    return team_with_members


@router.delete("/{team_id}")
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete team. Only owners can delete teams."""
    # Check if user is owner
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True,
        TeamMember.role == TeamRole.owner
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only team owners can delete teams."
        )
    
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    # Check if team has projects
    project_count = db.query(func.count(Project.id)).filter(Project.team_id == team_id).scalar()
    if project_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete team with {project_count} project(s). Please delete or move all projects first, or archive the team instead."
        )
    
    db.delete(team)
    db.commit()
    
    return {"message": "Team deleted successfully"}


# Team member management endpoints
@router.post("/{team_id}/members", response_model=TeamMemberDetailOut)
def add_team_member(
    team_id: int,
    payload: TeamMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a member to the team. Only owners and admins can add members."""
    # Check if current user has permission
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True,
        TeamMember.role.in_([TeamRole.owner, TeamRole.admin])
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only team owners and admins can add members."
        )
    
    # Check if team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    # Check if user exists
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Check if user is already a member
    existing_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == payload.user_id
    ).first()
    
    if existing_member:
        if existing_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this team"
            )
        else:
            # Reactivate the member
            existing_member.is_active = True
            existing_member.role = payload.role
            db.commit()
            db.refresh(existing_member)
            return existing_member
    
    # Add new member
    new_member = TeamMember(
        team_id=team_id,
        user_id=payload.user_id,
        role=payload.role
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    
    return new_member


@router.get("/{team_id}/members", response_model=List[TeamMemberDetailOut])
def list_team_members(
    team_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List team members. Only team members can view the member list."""
    # Check if user is a member of the team
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this team."
        )
    
    query = db.query(TeamMember).filter(TeamMember.team_id == team_id)
    if not include_inactive:
        query = query.filter(TeamMember.is_active == True)
    
    members = query.options(joinedload(TeamMember.user)).all()
    return members


@router.put("/{team_id}/members/{member_id}", response_model=TeamMemberDetailOut)
def update_team_member(
    team_id: int,
    member_id: int,
    payload: TeamMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update team member role or status. Only owners and admins can update members."""
    # Check if current user has permission
    current_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True,
        TeamMember.role.in_([TeamRole.owner, TeamRole.admin])
    ).first()
    
    if not current_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only team owners and admins can update members."
        )
    
    # Get the member to update
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id,
        TeamMember.team_id == team_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")
    
    # Prevent demoting the last owner
    if member.role == TeamRole.owner and payload.role and payload.role != TeamRole.owner:
        owner_count = db.query(func.count(TeamMember.id)).filter(
            TeamMember.team_id == team_id,
            TeamMember.role == TeamRole.owner,
            TeamMember.is_active == True
        ).scalar()
        
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last owner of the team"
            )
    
    # Update member
    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(member, field, value)
    
    db.commit()
    db.refresh(member)
    
    return member


@router.delete("/{team_id}/members/{member_id}")
def remove_team_member(
    team_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a member from the team. Only owners and admins can remove members."""
    # Check if current user has permission
    current_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True,
        TeamMember.role.in_([TeamRole.owner, TeamRole.admin])
    ).first()
    
    if not current_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only team owners and admins can remove members."
        )
    
    # Get the member to remove
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id,
        TeamMember.team_id == team_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")
    
    # Prevent removing the last owner
    if member.role == TeamRole.owner:
        owner_count = db.query(func.count(TeamMember.id)).filter(
            TeamMember.team_id == team_id,
            TeamMember.role == TeamRole.owner,
            TeamMember.is_active == True
        ).scalar()
        
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner of the team"
            )
    
    # Soft delete - deactivate the member
    member.is_active = False
    db.commit()
    
    return {"message": "Team member removed successfully"}


@router.get("/{team_id}/projects")
def list_team_projects(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List projects belonging to a team. Only team members can view projects."""
    # Check if user is a member of the team
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this team."
        )
    
    # Get all projects for this team
    projects = db.query(Project).filter(Project.team_id == team_id).all()
    
    return [
        {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status,  # Already a string, no need for .value
            "created_by": project.created_by,
            "created_at": project.created_at,
            "updated_at": project.updated_at
        }
        for project in projects
    ]


@router.post("/{team_id}/invite", response_model=InvitationResponse)
def invite_team_member(
    team_id: int,
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Invite a user to join the team by email. Only owners and admins can invite."""
    # Check if current user has permission to invite
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True,
        TeamMember.role.in_([TeamRole.owner, TeamRole.admin])
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only team owners and admins can invite members."
        )
    
    # Check if team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    # Check if user is already a member
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        existing_member = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == existing_user.id,
            TeamMember.is_active == True
        ).first()
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this team"
            )
    
    # Check if there's already a pending invitation for this email
    existing_invitation = db.query(Invitation).filter(
        Invitation.team_id == team_id,
        Invitation.email == payload.email,
        Invitation.status == 'pending'
    ).first()
    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An invitation has already been sent to this email"
        )
    
    # Create invitation
    invitation = create_invitation(
        db=db,
        team_id=team_id,
        email=payload.email,
        role=payload.role,
        invited_by_user_id=current_user.id
    )
    
    # Build invitation link
    invite_link = build_invitation_link(invitation.token)
    
    # Send invitation email via SMTP
    send_invitation_email_to_console(
        email=payload.email,
        invite_link=invite_link,
        team_name=team.name,
        inviter_name=current_user.full_name if hasattr(current_user, 'full_name') else current_user.username
    )
    
    # If the invited email belongs to an existing user, create an in-app notification
    invited_user = db.query(User).filter(User.email == payload.email).first()
    if invited_user:
        from app.models.notification import Notification, NotificationType
        notification = Notification(
            user_id=invited_user.id,
            type=NotificationType.TEAM_INVITATION,
            reference_id=team_id,
            title="Team Invitation",
            message=f"{current_user.full_name} has invited you to join the team '{team.name}' as {payload.role}.",
            is_read=False
        )
        db.add(notification)
        db.commit()
    
    return {
        "invite_link": invite_link,
        "status": invitation.status,
        "invitation": invitation
    }


@router.get("/{team_id}/invitations", response_model=List[InvitationOut])
def list_team_invitations(
    team_id: int,
    include_expired: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all invitations for a team.
    Only team owners and admins can view invitations.
    """
    # Check if current user has permission (owner or admin)
    team_member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == current_user.id,
        TeamMember.is_active == True,
        TeamMember.role.in_([TeamRole.owner, TeamRole.admin])
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only team owners and admins can view invitations."
        )
    
    # Check if team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    # Query invitations
    query = db.query(Invitation).filter(Invitation.team_id == team_id)
    
    if not include_expired:
        # Only show pending invitations by default
        query = query.filter(Invitation.status == 'pending')
    
    invitations = query.order_by(Invitation.created_at.desc()).all()
    
    # Update expired invitations
    for invitation in invitations:
        if invitation.status == 'pending' and invitation.is_expired():
            invitation.status = 'expired'
    
    db.commit()
    
    return invitations