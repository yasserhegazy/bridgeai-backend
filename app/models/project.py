import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ProjectStatus(enum.Enum):
    """Project approval status"""

    pending = "pending"  # Client created, waiting for BA approval
    approved = "approved"  # BA approved the project
    rejected = "rejected"  # BA rejected the project
    active = "active"  # Project is actively being worked on
    completed = "completed"  # Project is completed
    archived = "archived"  # Project is archived


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)  # No index - exact name search is rare
    description = Column(Text, nullable=True)
    team_id = Column(
        Integer, ForeignKey("teams.id"), nullable=False, index=True
    )  # CRITICAL: FK index for team filtering
    created_by = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )  # No index - creator lookups are rare

    # Approval workflow fields
    # For MySQL, we need to pass the enum values explicitly as strings
    status = Column(
        Enum(
            "pending",
            "approved",
            "rejected",
            "active",
            "completed",
            "archived",
            name="projectstatus",
        ),
        nullable=False,
        server_default="pending",
    )
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    approver = relationship("User", foreign_keys=[approved_by])
    team = relationship("Team", back_populates="projects")
