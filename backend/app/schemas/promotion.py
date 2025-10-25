from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PromotionBase(BaseModel):
    promotion_id: str
    name: str
    promotion_type: str
    store_scope: Optional[str] = None
    member_tier_scope: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    payload: str = "{}"


class PromotionCreate(PromotionBase):
    pass


class PromotionUpdate(BaseModel):
    name: Optional[str] = None
    promotion_type: Optional[str] = None
    store_scope: Optional[str] = None
    member_tier_scope: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    payload: Optional[str] = None


class PromotionRead(PromotionBase):
    id: int

    class Config:
        orm_mode = True
