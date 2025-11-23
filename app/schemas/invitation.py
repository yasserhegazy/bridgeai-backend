from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class InvitationCreate(BaseModel):
    """Schema for creating a team invitation."""
    email: EmailStr
    role: str = Field(..., pattern="^(owner|admin|member|viewer)$")


class InvitationOut(BaseModel):
    """Schema for invitation details."""
    id: int
    email: str
    role: str
    team_id: int
    invited_by_user_id: int
    token: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class InvitationPublicOut(BaseModel):
    """Public schema for invitation (without sensitive data)."""
    email: str
    role: str
    team_id: int
    team_name: Optional[str] = None
    status: str
    created_at: datetime
    expires_at: Optional[datetime]
    invited_by_name: Optional[str] = None
    invited_by_email: Optional[str] = None

    class Config:
        from_attributes = True


class InvitationResponse(BaseModel):
    """Response after creating invitation."""
    invite_link: str
    status: str
    invitation: InvitationOut


class InvitationAcceptResponse(BaseModel):
    """Response after accepting invitation."""
    message: str
    team_id: int
    role: str
