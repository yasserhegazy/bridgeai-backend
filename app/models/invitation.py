import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class InvitationStatus(enum.Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    canceled = "canceled"


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(
        String(256), nullable=False, index=True
    )  # Index for email lookups (high selectivity)
    role = Column(String(50), nullable=False)
    team_id = Column(
        Integer, ForeignKey("teams.id"), nullable=False, index=True
    )  # CRITICAL: FK index
    invited_by_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )  # No index - rarely query by inviter
    token = Column(
        String(64), nullable=False, unique=True, index=True
    )  # Unique = automatic index (for token validation)
    status = Column(
        Enum("pending", "accepted", "expired", "canceled", name="invitationstatus"),
        nullable=False,
        server_default="pending",
        index=True,  # Index for filtering pending invitations (moderate selectivity)
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # No index - rarely filtered by date
    expires_at = Column(
        DateTime(timezone=True), nullable=True
    )  # No index - cleanup can use status instead

    # Relationships
    team = relationship("Team")
    inviter = relationship("User", foreign_keys=[invited_by_user_id])

    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(self.expires_at.tzinfo) > self.expires_at

    def is_valid(self) -> bool:
        """Check if invitation is valid for acceptance."""
        return self.status == "pending" and not self.is_expired()
