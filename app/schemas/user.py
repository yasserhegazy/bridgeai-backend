from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum


class Role(str, Enum):
    client = "client"
    ba = "ba"
    admin = "admin"


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: Role


class Config:
    orm_mode = True