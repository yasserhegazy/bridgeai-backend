from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.notification import NotificationType
import re


class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=1000)
    type: NotificationType
    reference_id: int = Field(..., gt=0)
    
    @validator('title', 'message')
    def validate_text_fields(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('Field cannot be empty')
        dangerous_patterns = [r'<script', r'javascript:', r'onerror=', r'onclick=']
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Field contains invalid content')
        return v


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
