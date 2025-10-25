from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OrderItemPayload(BaseModel):
    sku_id: str
    qty: int
    price: float
    tax_rate: float = Field(default=0.0)


class OrderBase(BaseModel):
    order_id: str
    store_id: str
    channel: str = "POS"
    status: str = "CREATED"
    member_id: Optional[str] = None
    total: float
    tax_total: float = 0.0


class OrderCreate(OrderBase):
    items: List[OrderItemPayload]


class OrderUpdate(BaseModel):
    status: Optional[str] = None


class OrderRead(OrderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemPayload] = Field(default_factory=list)

    class Config:
        orm_mode = True
