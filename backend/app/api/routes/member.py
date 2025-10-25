from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_db, pagination_params
from app.models.base import Member
from app.schemas.member import MemberCreate, MemberRead, MemberUpdate

router = APIRouter(prefix="/members", tags=["members"])


@router.post("", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
def create_member(payload: MemberCreate, db: Session = Depends(get_db)) -> MemberRead:
    existing = db.exec(select(Member).where(Member.member_id == payload.member_id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Member already exists")
    member = Member(**payload.dict())
    db.add(member)
    db.commit()
    db.refresh(member)
    return MemberRead.from_orm(member)


@router.get("", response_model=list[MemberRead])
def list_members(
    pagination: tuple[int, int] = Depends(pagination_params),
    db: Session = Depends(get_db),
) -> list[MemberRead]:
    limit, offset = pagination
    query = select(Member).offset(offset).limit(limit)
    items = db.exec(query).all()
    return [MemberRead.from_orm(item) for item in items]


@router.get("/{member_id}", response_model=MemberRead)
def get_member(member_id: str, db: Session = Depends(get_db)) -> MemberRead:
    member = db.exec(select(Member).where(Member.member_id == member_id)).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return MemberRead.from_orm(member)


@router.patch("/{member_id}", response_model=MemberRead)
def update_member(member_id: str, payload: MemberUpdate, db: Session = Depends(get_db)) -> MemberRead:
    member = db.exec(select(Member).where(Member.member_id == member_id)).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(member, key, value)
    db.add(member)
    db.commit()
    db.refresh(member)
    return MemberRead.from_orm(member)
