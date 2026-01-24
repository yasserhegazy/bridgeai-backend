import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.sql import func

from app.db.session import Base


class CRSStatus(enum.Enum):
    draft = "draft"
    under_review = "under_review"
    approved = "approved"
    rejected = "rejected"


class CRSPattern(enum.Enum):
    """CRS Pattern/Standard selection for requirement documentation."""
    iso_iec_ieee_29148 = "iso_iec_ieee_29148"
    ieee_830 = "ieee_830"
    babok = "babok"


class CRSDocument(Base):
    __tablename__ = "crs_documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id"), nullable=False, index=True
    )  # CRITICAL: FK index
    created_by = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )  # No index - rarely query by creator
    content = Column(Text)  # structured JSON/text
    summary_points = Column(Text)  # main points extracted from chat
    pattern = Column(
        Enum(CRSPattern), default=CRSPattern.babok
    )  # CRS Standard/Pattern used
    field_sources = Column(
        Text, nullable=True
    )  # JSON mapping fields to sources (explicit_user_input vs llm_inference)
    status = Column(
        Enum(CRSStatus), default=CRSStatus.draft, index=True
    )  # CRITICAL: Frequently filtered (4-5 values, moderate selectivity)
    version = Column(Integer, default=1)  # No index - always queried with project_id
    edit_version = Column(
        Integer, default=1
    )  # Optimistic locking version for concurrent updates
    approved_by = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # No index - rarely queried
    rejection_reason = Column(Text, nullable=True)  # BA feedback when rejecting
    reviewed_at = Column(DateTime(timezone=True), nullable=True)  # When BA reviewed
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # No standalone index
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Composite index for: WHERE project_id=X AND status IN (...) ORDER BY created_at DESC
    __table_args__ = ({"mysql_engine": "InnoDB"},)
