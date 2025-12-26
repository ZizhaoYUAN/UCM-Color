"""Database access helpers."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas, security


class DuplicateUsernameError(RuntimeError):
    """Raised when trying to create a user with an existing username."""


def list_users(db: Session, *, skip: int = 0, limit: int = 50) -> list[models.User]:
    statement = select(models.User).offset(skip).limit(limit)
    return list(db.scalars(statement))


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.get(models.User, user_id)


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    statement = select(models.User).where(models.User.username == username)
    return db.scalars(statement).first()


def create_user(db: Session, payload: schemas.UserCreate) -> models.User:
    user = models.User(
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=security.hash_password(payload.password),
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateUsernameError(f"Username '{payload.username}' already exists") from exc
    db.refresh(user)
    return user


def update_user(db: Session, user: models.User, payload: schemas.UserUpdate) -> models.User:
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.email is not None:
        user.email = payload.email
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_superuser is not None:
        user.is_superuser = payload.is_superuser
    if payload.password:
        user.hashed_password = security.hash_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: models.User) -> None:
    db.delete(user)
    db.commit()


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """Return the matching user when the credentials are valid."""

    user = get_user_by_username(db, username)
    if not user or not user.is_active:
        return None
    if not security.verify_password(password, user.hashed_password):
        return None
    return user
