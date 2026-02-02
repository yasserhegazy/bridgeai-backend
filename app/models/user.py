import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class UserRole(enum.Enum):
    client = "client"
    ba = "ba"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(256), nullable=False)
    email = Column(String(256), unique=True, index=True, nullable=False)
    password_hash = Column(String(512), nullable=True)
    google_id = Column(String(128), unique=True, index=True, nullable=True)
    avatar_url = Column(String(512), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.client)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
