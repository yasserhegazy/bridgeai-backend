from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum
from app.models.user import UserRole


class Role(str, Enum):
    client = "client"
    ba = "ba"


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.client

class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: Role


class Config:
    orm_mode = True