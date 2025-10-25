from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Store(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    store_id: str = Field(index=True, unique=True)
    name: str
    region: Optional[str] = Field(default=None, index=True)
    timezone: str = Field(default="Asia/Shanghai")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SKU(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sku_id: str = Field(index=True, unique=True)
    name: str
    brand: Optional[str] = Field(default=None, index=True)
    category: Optional[str] = Field(default=None, index=True)
    tax_rate: float = Field(default=0.0)
    shelf_life_days: Optional[int] = Field(default=None)
    origin: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Barcode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sku_id: str = Field(foreign_key="sku.sku_id", index=True)
    code: str = Field(index=True, unique=True)
    package_size: Optional[str] = None


class Price(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    store_id: str = Field(foreign_key="store.store_id", index=True)
    sku_id: str = Field(foreign_key="sku.sku_id", index=True)
    price: float
    member_price: Optional[float] = Field(default=None)
    start_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    end_at: Optional[datetime] = Field(default=None, index=True)


class StockLedger(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    store_id: str = Field(foreign_key="store.store_id", index=True)
    sku_id: str = Field(foreign_key="sku.sku_id", index=True)
    qty_delta: int
    reason: str = Field(default="adjustment", index=True)
    reference: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Member(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: str = Field(index=True, unique=True)
    phone: Optional[str] = Field(default=None, index=True)
    tier: Optional[str] = Field(default="standard")
    tags: Optional[str] = Field(default="{}")
    is_blacklisted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: str = Field(index=True, unique=True)
    store_id: str = Field(foreign_key="store.store_id", index=True)
    channel: str = Field(default="POS", index=True)
    status: str = Field(default="CREATED", index=True)
    member_id: Optional[str] = Field(default=None, foreign_key="member.member_id", index=True)
    total: float = Field(default=0.0)
    tax_total: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: str = Field(foreign_key="order.order_id", index=True)
    sku_id: str = Field(foreign_key="sku.sku_id", index=True)
    qty: int
    price: float
    tax_rate: float = Field(default=0.0)


class Promotion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    promotion_id: str = Field(index=True, unique=True)
    name: str
    promotion_type: str = Field(index=True)
    store_scope: Optional[str] = Field(default=None)
    member_tier_scope: Optional[str] = Field(default=None)
    starts_at: datetime = Field(default_factory=datetime.utcnow)
    ends_at: Optional[datetime] = Field(default=None)
    payload: str = Field(default="{}")
