from typing import Generator

from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import session_scope


def get_db() -> Generator[Session, None, None]:
    with session_scope() as session:
        yield session


def pagination_params(limit: int = 50, offset: int = 0) -> tuple[int, int]:
    settings = get_settings()
    if limit > settings.max_page_size:
        limit = settings.max_page_size
    return limit, offset
