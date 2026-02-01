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
    role: Optional[UserRole] = UserRole.client
    
    


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
    role: Optional[UserRole] = UserRole.client


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    avatar_url: Optional[str] = None
    role: Role

    class Config:
        from_attributes = True
