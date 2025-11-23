from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum
from datetime import datetime, timedelta


class InvitationStatus(enum.Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    canceled = "canceled"


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(256), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # TeamRole value as string
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(64), nullable=False, unique=True, index=True)
    status = Column(
        Enum('pending', 'accepted', 'expired', 'canceled', name='invitationstatus'),
        nullable=False,
        server_default='pending'
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

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
        return self.status == 'pending' and not self.is_expired()
