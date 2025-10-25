from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlmodel import Session

from app.api.deps import get_db, pagination_params
from app.models.base import SKU, StockLedger
from app.schemas.inventory import StockBalance, StockLedgerRead, StockMove

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/moves", response_model=StockLedgerRead, status_code=status.HTTP_201_CREATED)
def record_stock_move(payload: StockMove, db: Session = Depends(get_db)) -> StockLedgerRead:
    sku_exists = db.exec(select(SKU).where(SKU.sku_id == payload.sku_id)).first()
    if not sku_exists:
        raise HTTPException(status_code=404, detail="SKU not found")

    entry = StockLedger(**payload.dict(), created_at=datetime.utcnow())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return StockLedgerRead.from_orm(entry)


@router.get("/ledger", response_model=list[StockLedgerRead])
def list_ledger(
    store_id: str | None = None,
    sku_id: str | None = None,
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
) -> list[StockLedgerRead]:
    limit, offset = pagination
    query = select(StockLedger)
    if store_id:
        query = query.where(StockLedger.store_id == store_id)
    if sku_id:
        query = query.where(StockLedger.sku_id == sku_id)
    query = query.order_by(StockLedger.created_at.desc()).offset(offset).limit(limit)
    results = db.exec(query).all()
    return [StockLedgerRead.from_orm(item) for item in results]


@router.get("/stock", response_model=list[StockBalance])
def list_stock_balances(
    store_id: str | None = None,
    sku_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[StockBalance]:
    query = (
        select(
            StockLedger.store_id,
            StockLedger.sku_id,
            func.coalesce(func.sum(StockLedger.qty_delta), 0).label("on_hand"),
            func.max(StockLedger.created_at).label("updated_at"),
        )
        .group_by(StockLedger.store_id, StockLedger.sku_id)
    )
    if store_id:
        query = query.where(StockLedger.store_id == store_id)
    if sku_id:
        query = query.where(StockLedger.sku_id == sku_id)

    rows = db.exec(query).all()
    return [
        StockBalance(store_id=row.store_id, sku_id=row.sku_id, on_hand=row.on_hand, updated_at=row.updated_at)
        for row in rows
    ]
