from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BarcodePayload(BaseModel):
    code: str = Field(..., description="Barcode value")
    package_size: Optional[str] = Field(default=None)


class PricePayload(BaseModel):
    store_id: str
    price: float
    member_price: Optional[float] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class SKUBase(BaseModel):
    sku_id: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    tax_rate: float = 0.0
    shelf_life_days: Optional[int] = None
    origin: Optional[str] = None


class SKUCreate(SKUBase):
    barcodes: List[BarcodePayload] = Field(default_factory=list)
    prices: List[PricePayload] = Field(default_factory=list)


class SKUUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    tax_rate: Optional[float] = None
    shelf_life_days: Optional[int] = None
    origin: Optional[str] = None
    barcodes: Optional[List[BarcodePayload]] = None
    prices: Optional[List[PricePayload]] = None


class SKURead(SKUBase):
    id: int
    created_at: datetime
    updated_at: datetime
    barcodes: List[BarcodePayload] = Field(default_factory=list)
    prices: List[PricePayload] = Field(default_factory=list)

    class Config:
        orm_mode = True
