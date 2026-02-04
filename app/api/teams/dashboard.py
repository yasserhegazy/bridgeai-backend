"""
Team Dashboard Module.
Handles team projects, invitations, and statistics.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.crs import CRSDocument
from app.models.invitation import Invitation
from app.models.project import Project
from app.models.session_model import SessionModel
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.invitation import InvitationCreate, InvitationOut, InvitationResponse
from app.schemas.team import (
    TeamDashboardStatsOut,
    ProjectStats,
    ChatStats,
    CRSStats,
    ProjectSimpleOut,
)
from app.utils.invitation import (
    build_invitation_link,
    create_invitation,
    send_invitation_email_to_console,
)
from app.services.permission_service import PermissionService

router = APIRouter()


@router.get("/{team_id}/projects")
def list_team_projects(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List projects belonging to a team. Only team members can view projects."""
    # Check if user is a member of the team
    team_member = (
        db.query(TeamMember)
        .filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.is_active == True,
        )
        .first()
    )

    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this team.",
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
            "updated_at": project.updated_at,
        }
        for project in projects
    ]


@router.post("/{team_id}/invite", response_model=InvitationResponse)
@limiter.limit("10/hour")
def invite_team_member(
    request: Request,
    team_id: int,
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite a user to join the team by email. Only owners and admins can invite."""
    # Check if current user has permission to invite
    PermissionService.verify_team_admin(db, team_id, current_user.id)

    # Check if team exists
    team = PermissionService.get_team_or_404(db, team_id)

    # Check if user is already a member
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        existing_member = (
            db.query(TeamMember)
            .filter(
                TeamMember.team_id == team_id,
                TeamMember.user_id == existing_user.id,
                TeamMember.is_active == True,
            )
            .first()
        )
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this team",
            )

    # Check if there's already a pending invitation for this email
    existing_invitation = (
        db.query(Invitation)
        .filter(
            Invitation.team_id == team_id,
            Invitation.email == payload.email,
            Invitation.status == "pending",
        )
        .first()
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
        email=payload.email,
        role=payload.role,
        invited_by_user_id=current_user.id,
    )

    # Build invitation link
    invite_link = build_invitation_link(invitation.token)

    # Send invitation email via SMTP
    send_invitation_email_to_console(
        email=payload.email,
        invite_link=invite_link,
        team_name=team.name,
        inviter_name=(
            current_user.full_name
            if hasattr(current_user, "full_name")
            else current_user.username
        ),
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
            is_read=False,
        )
        db.add(notification)
        db.commit()

    return {
        "invite_link": invite_link,
        "status": invitation.status,
        "invitation": invitation,
    }


@router.get("/{team_id}/invitations", response_model=List[InvitationOut])
def list_team_invitations(
    team_id: int,
    include_expired: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all invitations for a team.
    Only team owners and admins can view invitations.
    """
    # Check if current user has permission (owner or admin)
    PermissionService.verify_team_admin(db, team_id, current_user.id)

    # Check if team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )

    # Query invitations
    query = db.query(Invitation).filter(Invitation.team_id == team_id)

    if not include_expired:
        # Only show pending invitations by default
        query = query.filter(Invitation.status == "pending")

    invitations = query.order_by(Invitation.created_at.desc()).all()

    # Update expired invitations
    for invitation in invitations:
        if invitation.status == "pending" and invitation.is_expired():
            invitation.status = "expired"

    db.commit()

    return invitations


@router.delete("/{team_id}/invitations/{invitation_id}")
@limiter.limit("20/minute")
def cancel_invitation(
    request: Request,
    team_id: int,
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a pending invitation.
    Only team owners and admins can cancel invitations.
    """
    # Check if current user has permission (owner or admin)
    PermissionService.verify_team_admin(db, team_id, current_user.id)

    # Get the invitation
    invitation = (
        db.query(Invitation)
        .filter(Invitation.id == invitation_id, Invitation.team_id == team_id)
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
        )

    # Check if invitation can be canceled
    if invitation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel invitation with status: {invitation.status}",
        )

    # Update invitation status to canceled
    invitation.status = "canceled"
    db.commit()

    return {"message": "Invitation canceled successfully"}


@router.get("/{team_id}/dashboard/stats", response_model=TeamDashboardStatsOut)
def get_team_dashboard_stats(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get aggregated statistics for team dashboard.
    
    Returns:
    - Project counts by status
    - Chat counts by status (aggregated from all team projects)
    - CRS counts by status (aggregated from all team projects)
    - Top 10 recent projects
    """
    # Verify team access - check if user is a member of the team
    PermissionService.verify_team_membership(db, team_id, current_user.id)
    
    # Get all team projects
    team_projects = db.query(Project).filter(Project.team_id == team_id).all()
    project_ids = [p.id for p in team_projects]
    
    # Calculate project statistics
    project_stats_query = (
        db.query(Project.status, func.count(Project.id))
        .filter(Project.team_id == team_id)
        .group_by(Project.status)
        .all()
    )
    
    project_by_status = {status: count for status, count in project_stats_query}
    project_total = sum(project_by_status.values())
    
    # Calculate chat statistics (aggregated from all projects)
    chat_stats = {"total": 0, "by_status": {}}
    if project_ids:
        chat_stats_query = (
            db.query(SessionModel.status, func.count(SessionModel.id))
            .filter(SessionModel.project_id.in_(project_ids))
            .group_by(SessionModel.status)
            .all()
        )
        chat_stats["by_status"] = {
            status.value if hasattr(status, 'value') else str(status): count 
            for status, count in chat_stats_query
        }
        chat_stats["total"] = sum(chat_stats["by_status"].values())
    
    # Calculate CRS statistics (aggregated from all projects)
    crs_stats = {"total": 0, "by_status": {}}
    if project_ids:
        crs_stats_query = (
            db.query(CRSDocument.status, func.count(CRSDocument.id))
            .filter(CRSDocument.project_id.in_(project_ids))
            .group_by(CRSDocument.status)
            .all()
        )
        crs_stats["by_status"] = {
            status.value if hasattr(status, 'value') else str(status): count 
            for status, count in crs_stats_query
        }
        crs_stats["total"] = sum(crs_stats["by_status"].values())
    
    # Get top 10 recent projects
    recent_projects = (
        db.query(Project)
        .filter(Project.team_id == team_id)
        .order_by(Project.created_at.desc())
        .limit(3)
        .all()
    )
    
    return TeamDashboardStatsOut(
        projects=ProjectStats(
            total=project_total,
            by_status=project_by_status
        ),
        chats=ChatStats(
            total=chat_stats["total"],
            by_status=chat_stats["by_status"]
        ),
        crs=CRSStats(
            total=crs_stats["total"],
            by_status=crs_stats["by_status"]
        ),
        recent_projects=[
            ProjectSimpleOut(
                id=p.id,
                name=p.name,
                description=p.description,
                status=p.status.value if hasattr(p.status, 'value') else str(p.status),
                created_at=p.created_at
            )
            for p in recent_projects
        ]
    )
