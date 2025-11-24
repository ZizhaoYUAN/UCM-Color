"""Database utilities."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Base model for SQLAlchemy mappings."""


def _create_engine():
    settings = get_settings()
    return create_engine(
        f"sqlite:///{settings.database_path}", connect_args={"check_same_thread": False}, future=True
    )


def get_engine():
    """Return a lazily created engine instance."""

    global engine
    try:
        return engine
    except NameError:  # pragma: no cover - executed once at runtime
        engine = _create_engine()
        return engine


SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""

    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    """Ensure that the database schema exists."""

    from . import models  # noqa: F401 - ensure models are imported

    Base.metadata.create_all(bind=get_engine())
