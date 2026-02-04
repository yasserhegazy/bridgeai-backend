"""Repository for team invitation operations."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.invitation import Invitation
from app.repositories.base_repository import BaseRepository


class InvitationRepository(BaseRepository[Invitation]):
    """Repository for Invitation database operations."""

    def __init__(self, db: Session):
        """Initialize InvitationRepository."""
        super().__init__(Invitation, db)

    def get_by_token(self, token: str) -> Optional[Invitation]:
        """
        Get invitation by token.

        Args:
            token: Invitation token

        Returns:
            Invitation or None
        """
        return self.db.query(Invitation).filter(Invitation.token == token).first()

    def get_by_team_and_email(
        self, team_id: int, email: str, status: Optional[str] = None
    ) -> Optional[Invitation]:
        """
        Get invitation by team and email, optionally filtered by status.

        Args:
            team_id: Team ID
            email: Invitee email
            status: Optional invitation status to filter

        Returns:
            Invitation or None
        """
        query = self.db.query(Invitation).filter(
            and_(Invitation.team_id == team_id, Invitation.email == email)
        )
        if status:
            query = query.filter(Invitation.status == status)
        return query.first()

    def get_team_invitations(
        self,
        team_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Invitation]:
        """
        Get invitations for a team.

        Args:
            team_id: Team ID
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            List of invitations
        """
        query = self.db.query(Invitation).filter(Invitation.team_id == team_id)

        if status:
            query = query.filter(Invitation.status == status)

        return query.offset(skip).limit(limit).all()

    def update_status(self, invitation_id: int, status: str) -> Optional[Invitation]:
        """
        Update invitation status.

        Args:
            invitation_id: Invitation ID
            status: New status

        Returns:
            Updated invitation or None
        """
        invitation = self.get_by_id(invitation_id)
        if invitation:
            invitation.status = status
            self.db.commit()
            self.db.refresh(invitation)
        return invitation

    def get_user_invitations(self, email: str, status: Optional[str] = None) -> List[Invitation]:
        """
        Get invitations for a user by email.

        Args:
            email: User email
            status: Optional status filter

        Returns:
            List of invitations
        """
        query = self.db.query(Invitation).filter(Invitation.email == email)

        if status:
            query = query.filter(Invitation.status == status)

        return query.all()

    def delete_by_token(self, token: str) -> bool:
        """
        Delete invitation by token.

        Args:
            token: Invitation token

        Returns:
            True if deleted, False if not found
        """
        invitation = self.get_by_token(token)
        if invitation:
            self.db.delete(invitation)
            self.db.commit()
            return True
        return False
