"""
Team Members Module.
Handles team member management operations.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.team import Team, TeamMember, TeamRole
from app.models.user import User
from app.schemas.team import (
    TeamMemberCreate,
    TeamMemberDetailOut,
    TeamMemberUpdate,
)
from app.services.permission_service import PermissionService

router = APIRouter()


@router.post("/{team_id}/members", response_model=TeamMemberDetailOut)
def add_team_member(
    team_id: int,
    payload: TeamMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a member to the team. Only owners and admins can add members."""
    # Check if current user has permission
    PermissionService.verify_team_admin(db, team_id, current_user.id)

    # Check if team exists
    team = PermissionService.get_team_or_404(db, team_id)

    # Check if user exists
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if user is already a member
    existing_member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == payload.user_id)
        .first()
    )

    if existing_member:
        if existing_member.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this team",
            )
        else:
            # Reactivate the member
            existing_member.is_active = True
            existing_member.role = payload.role
            db.commit()
            db.refresh(existing_member)
            return existing_member

    # Add new member
    new_member = TeamMember(team_id=team_id, user_id=payload.user_id, role=payload.role)
    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return new_member


@router.get("/{team_id}/members", response_model=List[TeamMemberDetailOut])
def list_team_members(
    team_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List team members. Only team members can view the member list."""
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
    current_user: User = Depends(get_current_user),
):
    """Update team member role or status. Only owners and admins can update members."""
    # Check if current user has permission
    current_member = PermissionService.verify_team_admin(db, team_id, current_user.id)

    # Get the member to update
    member = (
        db.query(TeamMember)
        .filter(TeamMember.id == member_id, TeamMember.team_id == team_id)
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found"
        )

    # Prevent demoting the last owner
    if (
        member.role == TeamRole.owner
        and payload.role
        and payload.role != TeamRole.owner
    ):
        owner_count = (
            db.query(func.count(TeamMember.id))
            .filter(
                TeamMember.team_id == team_id,
                TeamMember.role == TeamRole.owner,
                TeamMember.is_active == True,
            )
            .scalar()
        )

        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last owner of the team",
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
    current_user: User = Depends(get_current_user),
):
    """Remove a member from the team. Only owners and admins can remove members."""
    # Check if current user has permission
    current_member = PermissionService.verify_team_admin(db, team_id, current_user.id)

    # Get the member to remove
    member = (
        db.query(TeamMember)
        .filter(TeamMember.id == member_id, TeamMember.team_id == team_id)
        .first()
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found"
        )

    # Prevent removing the last owner
    if member.role == TeamRole.owner:
        owner_count = (
            db.query(func.count(TeamMember.id))
            .filter(
                TeamMember.team_id == team_id,
                TeamMember.role == TeamRole.owner,
                TeamMember.is_active == True,
            )
            .scalar()
        )

        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner of the team",
            )

    # Soft delete - deactivate the member
    member.is_active = False
    db.commit()

    return {"message": "Team member removed successfully"}
