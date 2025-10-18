from sqlalchemy import Column, Integer, Text, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base
import enum


class CRSStatus(enum.Enum):
    draft = "draft"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"


class CRSDocument(Base):
    __tablename__ = "crs_documents"


    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text) # structured JSON/text
    summary_points = Column(Text) # main points extracted from chat
    status = Column(Enum(CRSStatus), default=CRSStatus.draft)
    version = Column(Integer, default=1)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())