"""CRS schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CRSPatternEnum(str, Enum):
    """Pydantic enum for CRS patterns."""

    iso_iec_ieee_29148 = "iso_iec_ieee_29148"
    ieee_830 = "ieee_830"
    babok = "babok"
    agile_user_stories = "agile_user_stories"


class CRSCreate(BaseModel):
    """Schema for creating a new CRS document."""

    project_id: int
    content: str
    summary_points: List[str] = Field(default_factory=list)
    allow_partial: bool = Field(
        default=False, description="Allow creation with incomplete data (draft status)"
    )
    completeness_percentage: Optional[int] = Field(
        None, description="Completeness percentage for partial CRS"
    )
    session_id: Optional[int] = Field(None, description="Session ID to link the CRS to")
    pattern: Optional[CRSPatternEnum] = Field(
        None,
        description="CRS Pattern (babok, ieee_830, iso_iec_ieee_29148, agile_user_stories)",
    )


class CRSStatusUpdate(BaseModel):
    """Schema for updating CRS status (approval workflow)."""

    status: str = Field(
        ..., description="New status: draft, under_review, approved, rejected"
    )
    rejection_reason: Optional[str] = Field(
        None, description="Reason for rejection (required when rejecting)"
    )


class CRSContentUpdate(BaseModel):
    """Schema for updating CRS content."""

    content: str = Field(..., description="Full JSON content of the CRS")
    field_sources: Optional[dict] = Field(
        None, description="Updated field sources if any"
    )
    edit_version: Optional[int] = Field(
        None, description="Expected version for optimistic locking"
    )


class CRSOut(BaseModel):
    """Schema for CRS document response."""

    id: int
    project_id: int
    status: str
    pattern: str
    version: int
    edit_version: int
    content: str
    summary_points: List[str]
    field_sources: Optional[dict] = None
    created_by: Optional[int] = None
    approved_by: Optional[int] = None
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogOut(BaseModel):
    """Schema for CRS audit log response."""

    id: int
    crs_id: int
    changed_by: int
    changed_at: datetime
    action: str
    old_status: Optional[str]
    new_status: Optional[str]
    old_content: Optional[str]
    new_content: Optional[str]
    summary: Optional[str]

    class Config:
        from_attributes = True


class CRSPreviewOut(BaseModel):
    """Schema for CRS preview response (not persisted)."""

    content: str
    summary_points: List[str]
    overall_summary: str
    is_complete: bool
    completeness_percentage: int
    missing_required_fields: List[str]
    missing_optional_fields: List[str]
    filled_optional_count: int
    weak_fields: List[str] = Field(default_factory=list)
    field_sources: dict = Field(default_factory=dict)
    project_id: int
    session_id: int
