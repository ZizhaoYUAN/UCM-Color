"""Authentication helpers for API and web handlers."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import crud, schemas, security
from .config import get_settings
from .dependencies import get_db

SESSION_COOKIE = "ucm_color_admin_user"


def _resolve_user(request: Request, db: Session) -> Optional[schemas.UserRead]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    settings = get_settings()
    username = security.verify_session(token, settings.secret_key)
    if not username:
        return None

    user = crud.get_user_by_username(db, username)
    if not user or not user.is_active:
        return None
    return schemas.UserRead.model_validate(user)


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> schemas.UserRead:
    """Require an authenticated, active user from the session cookie."""

    user = _resolve_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user
