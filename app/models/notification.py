import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

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
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )  # CRITICAL: FK index
    type = Column(String(50), nullable=False)  # No index - low selectivity (~8 types)
    reference_id = Column(
        Integer, nullable=False
    )  # No index - not queried independently
    title = Column(String(255), nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(
        Boolean, default=False, nullable=False
    )  # No index - only 2 values (very low selectivity)
    meta_data = Column(JSON, nullable=True)
    created_at = Column(
        DateTime, default=datetime.utcnow, nullable=False
    )  # No standalone index

    # Relationships
    user = relationship("User", back_populates="notifications")

    # Composite index covers: WHERE user_id=X AND is_read=Y ORDER BY created_at DESC
    # MySQL can use leftmost prefix for: WHERE user_id=X ORDER BY created_at
    __table_args__ = ({"mysql_engine": "InnoDB"},)
