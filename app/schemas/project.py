from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    team_id: int


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None


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