from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MemberBase(BaseModel):
    member_id: str
    phone: Optional[str] = None
    tier: Optional[str] = "standard"
    tags: Optional[str] = "{}"
    is_blacklisted: bool = False


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    phone: Optional[str] = None
    tier: Optional[str] = None
    tags: Optional[str] = None
    is_blacklisted: Optional[bool] = None


class MemberRead(MemberBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
