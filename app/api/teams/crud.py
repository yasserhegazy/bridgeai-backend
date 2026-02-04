"""
Teams CRUD Module.
Handles team creation, retrieval, updates, and deletion.
Refactored to use TeamService following service layer architecture.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.team import TeamStatus
from app.models.user import User
from app.schemas.team import (
    TeamCreate,
    TeamListOut,
    TeamOut,
    TeamUpdate,
)
from app.services.team_service import TeamService

router = APIRouter()


@router.post("/", response_model=TeamOut)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new team. The creator automatically becomes the owner."""
    return TeamService.create_team(db, payload.name, payload.description, current_user)


@router.get("/", response_model=List[TeamListOut])
def list_teams(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[TeamStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List teams. Users can see teams they are members of."""
    return TeamService.list_teams(db, current_user, skip, limit, status_filter)


@router.get("/{team_id}", response_model=TeamOut)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get team details. Only team members can view team details."""
    return TeamService.get_team(db, team_id, current_user)


@router.put("/{team_id}", response_model=TeamOut)
def update_team(
    team_id: int,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update team. Only owners and admins can update teams."""
    update_data = payload.dict(exclude_unset=True)
    return TeamService.update_team(
        db,
        team_id,
        current_user,
        name=update_data.get("name"),
        description=update_data.get("description"),
        status_update=update_data.get("status"),
    )
