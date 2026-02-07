import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator

from app.models.user import UserRole


class Role(str, Enum):
    client = "client"
    ba = "ba"


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr = Field(..., max_length=254)
    password: str = Field(..., min_length=8, max_length=128)
    # Role removed - will be selected post-registration via role selection modal
    
    


    @validator("full_name")
    def validate_full_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if not re.match(r"^[a-zA-Z\s\-\.]+$", v):
            raise ValueError(
                "Name can only contain letters, spaces, hyphens, and periods"
            )
        return v

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


class GoogleLoginRequest(BaseModel):
    token: str
    # Role removed - will be selected post-OAuth via role selection modal


class RoleSelectionRequest(BaseModel):
    """Request schema for selecting user role after registration/OAuth."""
    role: UserRole = Field(..., description="User role: 'client' or 'ba'")


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    avatar_url: Optional[str] = None
    role: Optional[Role] = None  # NULL indicates role not yet selected

    class Config:
        from_attributes = True
    
    @property
    def has_selected_role(self) -> bool:
        """Check if user has selected a role."""
        return self.role is not None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)


class UserProfileUpdate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)

    @validator("full_name")
    def validate_full_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if not re.match(r"^[a-zA-Z\s\-\.]+$", v):
            raise ValueError(
                "Name can only contain letters, spaces, hyphens, and periods"
            )
        return v


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @validator("new_password")
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v
