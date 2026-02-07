from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = None  # Role can be None for users who haven't selected yet
