from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.notification import NotificationType


class NotificationBase(BaseModel):
    title: str
    message: str
    type: NotificationType
    reference_id: int


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None  # Additional data for the notification

    class Config:
        from_attributes = True


class NotificationList(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int
    total_count: int


class NotificationMarkRead(BaseModel):
    is_read: bool = True
