import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from app.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = Field(None, max_length=2000)
    team_id: int = Field(..., gt=0)

    @validator("name")
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Project name cannot be empty")
        if not re.match(r"^[a-zA-Z0-9\s\-_\.]+$", v):
            raise ValueError(
                "Project name can only contain letters, numbers, spaces, hyphens, underscores, and periods"
            )
        return v

    @validator("description")
    def validate_description(cls, v):
        if v is not None:
            v = v.strip()
            # Check for script tags and other dangerous patterns
            dangerous_patterns = [r"<script", r"javascript:", r"onerror=", r"onclick="]
            for pattern in dangerous_patterns:
                if re.search(pattern, v, re.IGNORECASE):
                    raise ValueError("Description contains invalid content")
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[ProjectStatus] = None

    @validator("name")
    def validate_name(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Project name cannot be empty")
            if not re.match(r"^[a-zA-Z0-9\s\-_\.]+$", v):
                raise ValueError(
                    "Project name can only contain letters, numbers, spaces, hyphens, underscores, and periods"
                )
        return v

    @validator("description")
    def validate_description(cls, v):
        if v is not None:
            v = v.strip()
            dangerous_patterns = [r"<script", r"javascript:", r"onerror=", r"onclick="]
            for pattern in dangerous_patterns:
                if re.search(pattern, v, re.IGNORECASE):
                    raise ValueError("Description contains invalid content")
        return v


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    team_id: int
    created_by: int
    created_by_name: Optional[str] = None
    created_by_email: Optional[str] = None
    status: ProjectStatus
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectApprovalRequest(BaseModel):
    """Schema for approving a project"""

    pass  # No fields needed, just the action


class ProjectRejectionRequest(BaseModel):
    """Schema for rejecting a project"""

    rejection_reason: str = Field(..., min_length=1, max_length=500)

    @validator("rejection_reason")
    def validate_rejection_reason(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Rejection reason cannot be empty")
        dangerous_patterns = [r"<script", r"javascript:", r"onerror=", r"onclick="]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Rejection reason contains invalid content")
        return v


# Dashboard statistics schemas
class SessionSimpleOut(BaseModel):
    """Simple session schema for recent chats"""
    id: int
    name: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    message_count: int = 0

    class Config:
        from_attributes = True


class LatestCRSOut(BaseModel):
    """Latest CRS summary for dashboard"""
    id: int
    version: int
    status: str
    pattern: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectDashboardStatsOut(BaseModel):
    """Project dashboard aggregated statistics"""
    chats: Dict[str, Any] = {
        "total": 0,
        "by_status": {},
        "total_messages": 0
    }
    crs: Dict[str, Any] = {
        "total": 0,
        "by_status": {},
        "latest": None,
        "version_count": 0
    }
    documents: Dict[str, int] = {
        "total": 0
    }
    recent_chats: List[SessionSimpleOut] = []

    class Config:
        from_attributes = True
