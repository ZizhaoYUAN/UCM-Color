from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_db, pagination_params
from app.models.base import Store
from app.schemas.store import StoreCreate, StoreRead, StoreUpdate

router = APIRouter(prefix="/stores", tags=["stores"])


@router.post("", response_model=StoreRead, status_code=status.HTTP_201_CREATED)
def create_store(payload: StoreCreate, db: Session = Depends(get_db)) -> Store:
    existing = db.exec(select(Store).where(Store.store_id == payload.store_id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Store already exists")
    store = Store(**payload.dict())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("", response_model=list[StoreRead])
def list_stores(
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
) -> list[Store]:
    limit, offset = pagination
    query = select(Store).offset(offset).limit(limit)
    return db.exec(query).all()


@router.get("/{store_id}", response_model=StoreRead)
def get_store(store_id: str, db: Session = Depends(get_db)) -> Store:
    store = db.exec(select(Store).where(Store.store_id == store_id)).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.patch("/{store_id}", response_model=StoreRead)
def update_store(store_id: str, payload: StoreUpdate, db: Session = Depends(get_db)) -> Store:
    store = db.exec(select(Store).where(Store.store_id == store_id)).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(store, key, value)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store
