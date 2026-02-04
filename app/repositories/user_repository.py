"""User repository for database operations."""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.repositories.base_repository import BaseRepository
from app.models.user import User
from app.models.invitation import Invitation


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, db: Session):
        """
        Initialize UserRepository.

        Args:
            db: Database session
        """
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User or None if not found
        """
        return self.db.query(User).filter(User.email == email).first()

    def get_by_email_or_google_id(
        self, email: str, google_id: Optional[str] = None
    ) -> Optional[User]:
        """
        Get user by email or Google ID.

        Args:
            email: User email
            google_id: Google ID (optional)

        Returns:
            User or None if not found
        """
        if google_id:
            return (
                self.db.query(User)
                .filter(or_(User.email == email, User.google_id == google_id))
                .first()
            )
        return self.get_by_email(email)

    def get_pending_invitations(self, email: str) -> List[Invitation]:
        """
        Get all pending invitations for a user email.

        Args:
            email: User email

        Returns:
            List of pending invitations
        """
        return (
            self.db.query(Invitation)
            .filter(Invitation.email == email, Invitation.status == "pending")
            .all()
        )

    def delete_invitations_by_email(self, email: str) -> None:
        """
        Delete all invitations for a user email.

        Args:
            email: User email
        """
        self.db.query(Invitation).filter(Invitation.email == email).delete()
        self.db.flush()
