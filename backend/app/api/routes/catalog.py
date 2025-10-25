from datetime import datetime
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete
from sqlmodel import Session, select

from app.api.deps import get_db, pagination_params
from app.models.base import Barcode, Price, SKU
from app.schemas.catalog import BarcodePayload, PricePayload, SKUCreate, SKURead, SKUUpdate

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post("/skus", response_model=SKURead, status_code=status.HTTP_201_CREATED)
def create_sku(payload: SKUCreate, db: Session = Depends(get_db)) -> SKU:
    sku = SKU(**payload.dict(exclude={"barcodes", "prices"}))
    db.add(sku)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="SKU already exists") from exc
    db.refresh(sku)

    _sync_barcodes(db, sku.sku_id, payload.barcodes)
    _sync_prices(db, sku.sku_id, payload.prices)
    db.refresh(sku)
    return _load_full_sku(db, sku.sku_id)


@router.get("/skus", response_model=list[SKURead])
def list_skus(
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
) -> list[SKURead]:
    limit, offset = pagination
    results = db.exec(select(SKU).offset(offset).limit(limit)).all()
    return [_load_full_sku(db, sku.sku_id) for sku in results]


@router.get("/skus/{sku_id}", response_model=SKURead)
def get_sku(sku_id: str, db: Session = Depends(get_db)) -> SKURead:
    sku = _load_full_sku(db, sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")
    return sku


@router.patch("/skus/{sku_id}", response_model=SKURead)
def update_sku(sku_id: str, payload: SKUUpdate, db: Session = Depends(get_db)) -> SKURead:
    sku = db.exec(select(SKU).where(SKU.sku_id == sku_id)).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")

    update_data = payload.dict(exclude_unset=True, exclude={"barcodes", "prices"})
    for key, value in update_data.items():
        setattr(sku, key, value)
    sku.updated_at = datetime.utcnow()
    db.add(sku)
    db.commit()

    if payload.barcodes is not None:
        _sync_barcodes(db, sku_id, payload.barcodes)
    if payload.prices is not None:
        _sync_prices(db, sku_id, payload.prices)

    db.refresh(sku)
    return _load_full_sku(db, sku_id)


def _load_full_sku(db: Session, sku_id: str) -> SKURead | None:
    sku = db.exec(select(SKU).where(SKU.sku_id == sku_id)).first()
    if not sku:
        return None
    barcodes = db.exec(select(Barcode).where(Barcode.sku_id == sku_id)).all()
    prices = db.exec(select(Price).where(Price.sku_id == sku_id)).all()
    return SKURead(
        **sku.dict(),
        barcodes=[{"code": b.code, "package_size": b.package_size} for b in barcodes],
        prices=[
            {
                "store_id": p.store_id,
                "price": p.price,
                "member_price": p.member_price,
                "start_at": p.start_at,
                "end_at": p.end_at,
            }
            for p in prices
        ],
    )


def _sync_barcodes(db: Session, sku_id: str, payloads: Iterable[BarcodePayload]) -> None:
    db.exec(delete(Barcode).where(Barcode.sku_id == sku_id))
    for item in payloads:
        barcode = Barcode(sku_id=sku_id, code=item.code, package_size=item.package_size)
        db.add(barcode)
    db.commit()



def _sync_prices(db: Session, sku_id: str, payloads: Iterable[PricePayload]) -> None:
    db.exec(delete(Price).where(Price.sku_id == sku_id))
    for item in payloads:
        price = Price(
            store_id=item.store_id,
            sku_id=sku_id,
            price=item.price,
            member_price=item.member_price,
            start_at=item.start_at or datetime.utcnow(),
            end_at=item.end_at,
        )
        db.add(price)
    db.commit()
