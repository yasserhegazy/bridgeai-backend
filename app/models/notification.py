from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.session import Base


class NotificationType(str, enum.Enum):
    PROJECT_APPROVAL = "project_approval"
    TEAM_INVITATION = "team_invitation"
    CRS_CREATED = "crs_created"
    CRS_UPDATED = "crs_updated"
    CRS_STATUS_CHANGED = "crs_status_changed"
    CRS_COMMENT_ADDED = "crs_comment_added"
    CRS_APPROVED = "crs_approved"
    CRS_REJECTED = "crs_rejected"
    CRS_REVIEW_ASSIGNED = "crs_review_assigned"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    reference_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")
