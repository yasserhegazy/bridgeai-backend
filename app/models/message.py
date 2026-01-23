import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.sql import func

from app.db.session import Base


class SenderType(enum.Enum):
    client = "client"
    ai = "ai"
    ba = "ba"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer, ForeignKey("sessions.id"), nullable=False, index=True
    )  # CRITICAL: FK index for session queries
    sender_type = Column(Enum(SenderType), nullable=False)
    sender_id = Column(
        Integer, ForeignKey("users.id"), nullable=True
    )  # No index - rarely queried by sender
    content = Column(Text, nullable=False)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # No standalone index - covered by composite

    # Composite index for common query: WHERE session_id=X ORDER BY timestamp DESC
    __table_args__ = ({"mysql_engine": "InnoDB"},)
