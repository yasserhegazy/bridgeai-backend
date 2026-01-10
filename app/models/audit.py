from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Text
from sqlalchemy.sql import func
from app.db.session import Base

class CRSAuditLog(Base):
    __tablename__ = "crs_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    crs_id = Column(Integer, ForeignKey("crs_documents.id"), nullable=False, index=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    action = Column(String(50), nullable=False)  # e.g., "created", "status_updated", "content_updated"
    old_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=True)
    old_content = Column(Text, nullable=True)
    new_content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)  # optional human‑readable description
