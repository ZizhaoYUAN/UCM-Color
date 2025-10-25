from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlmodel import Session

from app.api.deps import get_db, pagination_params
from app.models.base import Order, OrderItem, SKU, StockLedger, Store
from app.schemas.order import OrderCreate, OrderRead, OrderUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> OrderRead:
    if not db.exec(select(Store).where(Store.store_id == payload.store_id)).first():
        raise HTTPException(status_code=404, detail="Store not found")

    for item in payload.items:
        if not db.exec(select(SKU).where(SKU.sku_id == item.sku_id)).first():
            raise HTTPException(status_code=404, detail=f"SKU {item.sku_id} not found")

    existing = db.exec(select(Order).where(Order.order_id == payload.order_id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Order already exists")

    order = Order(
        order_id=payload.order_id,
        store_id=payload.store_id,
        channel=payload.channel,
        status=payload.status,
        member_id=payload.member_id,
        total=payload.total,
        tax_total=payload.tax_total,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    for item in payload.items:
        order_item = OrderItem(
            order_id=payload.order_id,
            sku_id=item.sku_id,
            qty=item.qty,
            price=item.price,
            tax_rate=item.tax_rate,
        )
        db.add(order_item)
        ledger = StockLedger(
            store_id=payload.store_id,
            sku_id=item.sku_id,
            qty_delta=-abs(item.qty),
            reason="sale",
            reference=payload.order_id,
            created_at=datetime.utcnow(),
        )
        db.add(ledger)
    db.commit()

    return _load_order(db, payload.order_id)


@router.get("", response_model=list[OrderRead])
def list_orders(
    store_id: str | None = None,
    status_filter: str | None = None,
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
) -> list[OrderRead]:
    limit, offset = pagination
    query = select(Order)
    if store_id:
        query = query.where(Order.store_id == store_id)
    if status_filter:
        query = query.where(Order.status == status_filter)
    query = query.order_by(Order.created_at.desc()).offset(offset).limit(limit)
    orders = db.exec(query).all()
    return [_load_order(db, order.order_id) for order in orders]


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: str, db: Session = Depends(get_db)) -> OrderRead:
    order = _load_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}", response_model=OrderRead)
def update_order(order_id: str, payload: OrderUpdate, db: Session = Depends(get_db)) -> OrderRead:
    order = db.exec(select(Order).where(Order.order_id == order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)
    order.updated_at = datetime.utcnow()
    db.add(order)
    db.commit()
    db.refresh(order)
    return _load_order(db, order_id)


def _load_order(db: Session, order_id: str) -> OrderRead | None:
    order = db.exec(select(Order).where(Order.order_id == order_id)).first()
    if not order:
        return None
    items = db.exec(select(OrderItem).where(OrderItem.order_id == order_id)).all()
    return OrderRead(
        **order.dict(),
        items=[
            {
                "sku_id": item.sku_id,
                "qty": item.qty,
                "price": item.price,
                "tax_rate": item.tax_rate,
            }
            for item in items
        ],
    )
