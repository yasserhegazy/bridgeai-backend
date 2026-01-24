from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class SessionStatusEnum(str, Enum):
    active = "active"
    completed = "completed"


class SenderTypeEnum(str, Enum):
    client = "client"
    ai = "ai"
    ba = "ba"


class CRSPatternEnum(str, Enum):
    iso_iec_ieee_29148 = "iso_iec_ieee_29148"
    ieee_830 = "ieee_830"
    babok = "babok"
    agile_user_stories = "agile_user_stories"


# Message Schemas
class MessageBase(BaseModel):
    content: str
    sender_type: SenderTypeEnum


class MessageCreate(MessageBase):
    pass


class MessageOut(MessageBase):
    id: int
    session_id: int
    sender_id: Optional[int]
    timestamp: datetime

    class Config:
        from_attributes = True


# Session/Chat Schemas
class SessionBase(BaseModel):
    name: str


class SessionCreate(SessionBase):
    crs_document_id: Optional[int] = None
    crs_pattern: Optional[CRSPatternEnum] = CRSPatternEnum.babok


class SessionUpdate(BaseModel):
    status: Optional[SessionStatusEnum] = None
    name: Optional[str] = None


class SessionOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    crs_document_id: Optional[int] = None
    crs_pattern: Optional[str] = None
    name: str
    status: SessionStatusEnum

    started_at: datetime
    ended_at: Optional[datetime]
    messages: List[MessageOut] = []

    class Config:
        from_attributes = True


class SessionListOut(BaseModel):
    id: int
    project_id: int
    user_id: int
    crs_document_id: Optional[int] = None
    crs_pattern: Optional[str] = None
    name: str
    status: SessionStatusEnum

    started_at: datetime
    ended_at: Optional[datetime]
    message_count: int

    class Config:
        from_attributes = True
