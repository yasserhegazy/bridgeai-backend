from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base
import enum


class SourceType(enum.Enum):
    crs = "crs"
    message = "message"
    comment = "comment"
    summary = "summary"


class AIMemoryIndex(Base):
    __tablename__ = "ai_memory_index"


    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    source_id = Column(Integer, nullable=False)
    embedding_id = Column(String(256), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())