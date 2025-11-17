"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from .database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for FastAPI routes."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
