from pydantic import BaseModel
from typing import Optional


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    team_id: int


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    team_id: int

    class Config:
        from_attributes = True