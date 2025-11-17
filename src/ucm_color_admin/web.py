"""Minimal HTML front-end for the admin backend."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import crud, schemas
from .dependencies import get_db

router = APIRouter(prefix="/web", include_in_schema=False)
_templates_dir = Path(__file__).with_name("templates")
templates = Jinja2Templates(directory=str(_templates_dir))
_SESSION_COOKIE = "ucm_color_admin_user"
_SESSION_AGE = 60 * 60 * 8  # 8 hours


def _current_user(request: Request, db: Session) -> Optional[schemas.UserRead]:
    username = request.cookies.get(_SESSION_COOKIE)
    if not username:
        return None
    user = crud.get_user_by_username(db, username)
    if not user:
        return None
    return schemas.UserRead.model_validate(user)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, message: str | None = None, db: Session = Depends(get_db)):
    current_user = _current_user(request, db)
    if current_user:
        return RedirectResponse(url="/web/forms", status_code=status.HTTP_303_SEE_OTHER)
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "message": message,
            "error": "请登录以访问控制台" if error == "login_required" else None,
        },
    )


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = crud.authenticate_user(db, username=username, password=password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "用户名或密码错误", "message": None},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    response = RedirectResponse(url="/web/forms", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=_SESSION_COOKIE,
        value=user.username,
        httponly=True,
        samesite="lax",
        max_age=_SESSION_AGE,
    )
    return response


@router.get("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse(url="/web/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(_SESSION_COOKIE)
    return response


@router.get("/forms", response_class=HTMLResponse)
def forms_page(request: Request, message: str | None = None, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login?error=login_required", status_code=status.HTTP_303_SEE_OTHER)
    users = crud.list_users(db, limit=200)
    return templates.TemplateResponse(
        "forms.html",
        {"request": request, "users": users, "message": message, "current_user": user},
    )


def _bool_from_form(value: Optional[str]) -> bool:
    return value == "true"


def _redirect_with_message(message: str) -> RedirectResponse:
    encoded = quote_plus(message)
    return RedirectResponse(url=f"/web/forms?message={encoded}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/forms/create")
def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    email: str = Form(""),
    is_active: str = Form("true"),
    is_superuser: str = Form("false"),
    db: Session = Depends(get_db),
):
    if not _current_user(request, db):
        return RedirectResponse(url="/web/login?error=login_required", status_code=status.HTTP_303_SEE_OTHER)
    payload = schemas.UserCreate(
        username=username,
        password=password,
        full_name=full_name or None,
        email=email or None,
        is_active=_bool_from_form(is_active),
        is_superuser=_bool_from_form(is_superuser),
    )
    try:
        crud.create_user(db, payload)
        msg = "成功创建用户"
    except crud.DuplicateUsernameError:
        msg = "用户名已存在"
    return _redirect_with_message(msg)


@router.post("/forms/update")
def update_user(
    request: Request,
    user_id: int = Form(...),
    full_name: str = Form(""),
    email: str = Form(""),
    is_active: str = Form("keep"),
    is_superuser: str = Form("keep"),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    if not _current_user(request, db):
        return RedirectResponse(url="/web/login?error=login_required", status_code=status.HTTP_303_SEE_OTHER)
    user = crud.get_user(db, user_id)
    if not user:
        return _redirect_with_message("用户不存在")
    payload = schemas.UserUpdate(
        full_name=full_name or None,
        email=email or None,
        is_active=None if is_active == "keep" else _bool_from_form(is_active),
        is_superuser=None if is_superuser == "keep" else _bool_from_form(is_superuser),
        password=password or None,
    )
    crud.update_user(db, user, payload)
    return _redirect_with_message("用户已更新")


@router.post("/forms/delete")
def delete_user(
    request: Request,
    user_id: int = Form(...),
    db: Session = Depends(get_db),
):
    if not _current_user(request, db):
        return RedirectResponse(url="/web/login?error=login_required", status_code=status.HTTP_303_SEE_OTHER)
    user = crud.get_user(db, user_id)
    if not user:
        msg = "用户不存在"
    else:
        crud.delete_user(db, user)
        msg = "用户已删除"
    return _redirect_with_message(msg)
