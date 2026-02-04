"""
Teams CRUD Module.
Handles team creation, retrieval, updates, and deletion.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.team import Team, TeamMember, TeamRole, TeamStatus
from app.models.user import User
from app.schemas.team import (
    TeamCreate,
    TeamListOut,
    TeamOut,
    TeamUpdate,
)
from app.services.permission_service import PermissionService

router = APIRouter()


@router.post("/", response_model=TeamOut)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new team. The creator automatically becomes the owner."""
    # Check if team name already exists for this user
    existing_team = (
        db.query(Team)
        .filter(Team.name == payload.name, Team.created_by == current_user.id)
        .first()
    )
    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a team with this name",
        )

    # Create the team
    team = Team(
        name=payload.name, description=payload.description, created_by=current_user.id
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    # Add creator as owner
    team_member = TeamMember(
        team_id=team.id, user_id=current_user.id, role=TeamRole.owner
    )
    db.add(team_member)
    db.commit()

    # Return team with members
    team_with_members = (
        db.query(Team)
        .options(joinedload(Team.members))
        .filter(Team.id == team.id)
        .first()
    )
    return team_with_members


@router.get("/", response_model=List[TeamListOut])
def list_teams(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[TeamStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List teams. Users can see teams they are members of."""
    query = (
        db.query(Team)
        .join(TeamMember)
        .filter(TeamMember.user_id == current_user.id, TeamMember.is_active == True)
    )

    if status_filter:
        query = query.filter(Team.status == status_filter)

    teams = query.offset(skip).limit(limit).all()

    # Add member count to each team
    result = []
    for team in teams:
        member_count = (
            db.query(func.count(TeamMember.id))
            .filter(TeamMember.team_id == team.id, TeamMember.is_active == True)
            .scalar()
        )

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


@router.get("/{team_id}", response_model=TeamOut)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get team details. Only team members can view team details."""
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

    team = (
        db.query(Team)
        .options(joinedload(Team.members))
        .filter(Team.id == team_id)
        .first()
    )
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )

    return team


@router.put("/{team_id}", response_model=TeamOut)
def update_team(
    team_id: int,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update team. Only owners and admins can update teams."""
    # Check if user has permission (owner or admin)
    PermissionService.verify_team_admin(db, team_id, current_user.id)

    team = PermissionService.get_team_or_404(db, team_id)

    # Validate that only allowed fields are being updated
    update_data = payload.dict(exclude_unset=True)

    # Check if user is trying to update name to one that already exists for them
    if "name" in update_data and update_data["name"] != team.name:
        existing_team = (
            db.query(Team)
            .filter(
                Team.name == update_data["name"],
                Team.created_by == current_user.id,
                Team.id != team_id,  # Exclude current team
            )
            .first()
        )
        if existing_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have another team with this name",
            )

    # Update team fields
    for field, value in update_data.items():
        setattr(team, field, value)

    db.commit()
    db.refresh(team)

    # Return team with members
    team_with_members = (
        db.query(Team)
        .options(joinedload(Team.members))
        .filter(Team.id == team.id)
        .first()
    )
    return team_with_members


@router.delete("/{team_id}")
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete team. Only owners can delete teams."""
    # Check if user is owner
    PermissionService.verify_team_owner(db, team_id, current_user.id)

    team = PermissionService.get_team_or_404(db, team_id)

    # Check if team has projects
    project_count = (
        db.query(func.count(Project.id)).filter(Project.team_id == team_id).scalar()
    )
    if project_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete team with {project_count} project(s). Please delete or move all projects first, or archive the team instead.",
        )

    db.delete(team)
    db.commit()

    return {"message": "Team deleted successfully"}
