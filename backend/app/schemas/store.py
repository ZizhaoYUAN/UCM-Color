from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StoreBase(BaseModel):
    store_id: str
    name: str
    region: Optional[str] = None
    timezone: str = "Asia/Shanghai"


class StoreCreate(StoreBase):
    pass


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None
    timezone: Optional[str] = None


class StoreRead(StoreBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
