"""
Team Dashboard Module.
Handles team projects, invitations, and statistics.
Refactored to use TeamService following service layer architecture.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.crs import CRSDocument
from app.models.project import Project
from app.models.session_model import SessionModel
from app.models.user import User
from app.schemas.invitation import InvitationCreate, InvitationOut, InvitationResponse
from app.schemas.team import (
    TeamDashboardStatsOut,
    ProjectStats,
    ChatStats,
    CRSStats,
    ProjectSimpleOut,
)
from app.services.permission_service import PermissionService
from app.services.team_service import TeamService

router = APIRouter()


@router.get("/{team_id}/projects")
def list_team_projects(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List projects belonging to a team. Only team members can view projects."""
    return TeamService.list_team_projects(db, team_id, current_user)


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
    return TeamService.invite_member(db, team_id, payload.email, payload.role, current_user)


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
    return TeamService.list_invitations(db, team_id, current_user, include_expired)


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
    return TeamService.cancel_invitation(db, team_id, invitation_id, current_user)


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
