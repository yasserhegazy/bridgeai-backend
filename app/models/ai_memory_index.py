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
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)  # CRITICAL: FK index
    source_type = Column(Enum(SourceType), nullable=False)  # No index - if needed, use composite with project_id
    source_id = Column(Integer, nullable=False)  # No index - not queried independently
    embedding_id = Column(String(256), nullable=False, unique=True, index=True)  # Unique constraint = automatic index
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # No index - rarely queried
    
    # Note: Vector search happens in ChromaDB, MySQL is just metadata lookup
    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )