import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class SessionStatus(enum.Enum):
    active = "active"
    completed = "completed"



class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    crs_document_id = Column(
        Integer,
        ForeignKey("crs_documents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    crs_pattern = Column(String(50), nullable=True, default="babok")
    name = Column(String(255), nullable=False)
    status = Column(Enum(SessionStatus), default=SessionStatus.active)
    
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    messages = relationship("Message", backref="session", order_by="Message.timestamp")
