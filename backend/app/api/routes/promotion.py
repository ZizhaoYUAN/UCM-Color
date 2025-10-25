from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_db, pagination_params
from app.models.base import Promotion
from app.schemas.promotion import PromotionCreate, PromotionRead, PromotionUpdate

router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.post("", response_model=PromotionRead, status_code=status.HTTP_201_CREATED)
def create_promotion(payload: PromotionCreate, db: Session = Depends(get_db)) -> PromotionRead:
    existing = db.exec(select(Promotion).where(Promotion.promotion_id == payload.promotion_id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Promotion already exists")
    promotion = Promotion(
        promotion_id=payload.promotion_id,
        name=payload.name,
        promotion_type=payload.promotion_type,
        store_scope=payload.store_scope,
        member_tier_scope=payload.member_tier_scope,
        starts_at=payload.starts_at or datetime.utcnow(),
        ends_at=payload.ends_at,
        payload=payload.payload,
    )
    db.add(promotion)
    db.commit()
    db.refresh(promotion)
    return PromotionRead.from_orm(promotion)


@router.get("", response_model=list[PromotionRead])
def list_promotions(
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
) -> list[PromotionRead]:
    limit, offset = pagination
    query = select(Promotion).offset(offset).limit(limit)
    items = db.exec(query).all()
    return [PromotionRead.from_orm(item) for item in items]


@router.get("/{promotion_id}", response_model=PromotionRead)
def get_promotion(promotion_id: str, db: Session = Depends(get_db)) -> PromotionRead:
    promotion = db.exec(select(Promotion).where(Promotion.promotion_id == promotion_id)).first()
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return PromotionRead.from_orm(promotion)


@router.patch("/{promotion_id}", response_model=PromotionRead)
def update_promotion(promotion_id: str, payload: PromotionUpdate, db: Session = Depends(get_db)) -> PromotionRead:
    promotion = db.exec(select(Promotion).where(Promotion.promotion_id == promotion_id)).first()
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(promotion, key, value)
    if "starts_at" in update_data and promotion.starts_at is None:
        promotion.starts_at = datetime.utcnow()
    db.add(promotion)
    db.commit()
    db.refresh(promotion)
    return PromotionRead.from_orm(promotion)
