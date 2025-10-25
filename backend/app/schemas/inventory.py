from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class StockMove(BaseModel):
    store_id: str
    sku_id: str
    qty_delta: int = Field(..., description="Positive for inbound, negative for outbound")
    reason: str = Field(default="adjustment")
    reference: Optional[str] = None


class StockLedgerRead(StockMove):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class StockBalance(BaseModel):
    store_id: str
    sku_id: str
    on_hand: int
    updated_at: datetime
