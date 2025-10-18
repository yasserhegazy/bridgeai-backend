from sqlalchemy import Column, Integer, Text, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base
import enum


class SenderType(enum.Enum):
    client = "client"
    ai = "ai"
    ba = "ba"


class Message(Base):
    __tablename__ = "messages"


    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    sender_type = Column(Enum(SenderType), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())