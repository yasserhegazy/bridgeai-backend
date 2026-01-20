from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
import enum


class SessionStatus(enum.Enum):
    active = "active"
    completed = "completed"


class CRSPattern(enum.Enum):
    """CRS Pattern/Standard selection for requirement documentation."""
    iso_iec_ieee_29148 = "iso_iec_ieee_29148"
    ieee_830 = "ieee_830"
    babok = "babok"


class SessionModel(Base):
    __tablename__ = "sessions"


    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    crs_document_id = Column(Integer, ForeignKey("crs_documents.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(Enum(SessionStatus), default=SessionStatus.active)
    crs_pattern = Column(Enum(CRSPattern), default=CRSPattern.babok)  # CRS pattern/standard selection
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    messages = relationship("Message", backref="session", order_by="Message.timestamp")