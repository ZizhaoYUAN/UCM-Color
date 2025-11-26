"""Minimal HTML front-end for the admin backend."""

from __future__ import annotations

from dataclasses import dataclass
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

@dataclass(frozen=True)
class MenuItem:
    label: str
    children: tuple["MenuItem", ...] = ()


@dataclass(frozen=True)
class Module:
    """Descriptor for dashboard checklist sections."""

    id: str
    title: str
    summary: str
    checklist: list[str]
    menu: tuple[MenuItem, ...] = ()


_MODULES: list[Module] = [
    Module(
        id="catalog",
        title="商品（Catalog）",
        summary="条码、价格、富媒体与批量导入导出能力",
        checklist=[
            "商品列表字段：SKU、商品条码（支持多条码输入）、分类、包装规格、单位",
            "价格管理：销售价/会员价/生鲜临时调价，均含生效时间",
            "税率、品牌、产地、保质期属性可维护且可查询",
            "图片与富媒体：商品图片最多 5 张、商品视频可上传到对象存储",
            "批量导入/导出：CSV/Excel，导入前校验并支持差异预览",
            "商品列表含查询、导入、导出、编辑与新增商品按钮",
        ],
        menu=(MenuItem(label="商品", children=(MenuItem(label="新增商品"),)),),
    ),
    Module(
        id="inventory",
        title="库存（Inventory）",
        summary="库存流水、盘点、预警与门店调拨流程",
        checklist=[
            "库存流水 Ledger：入库/退货/报损/盘盈/调拨/销售扣减",
            "盘点：差异对账、生成调整单",
            "可卖量 ATS：在线计算 + 预聚合缓存",
            "预警：低库存阈值、滞销告警",
            "库存查询列表，导出和导入",
            "门店商品库存调拔",
        ],
    ),
    Module(
        id="crm",
        title="会员（CRM）",
        summary="会员档案、积分与合规导出申请",
        checklist=[
            "会员档案：手机号/标签/黑名单/合并（重复号码、无效记录）",
            "积分（可选）：获取/消费规则",
            "隐私合规：脱敏展示、导出申请",
            "会员的等级设和优惠设置",
            "会员清费历史记录",
        ],
    ),
    Module(
        id="orders",
        title="订单（OMS/Orders）",
        summary="订单状态流、售后与对账",
        checklist=[
            "查询/筛选：按时间/店/渠道/状态/会员/金额",
            "状态流：CREATED → PAID → READY → HANDED_OVER/DELIVERED → CLOSED",
            "售后：退款/作废（权限控制、双人复核可选）",
            "对账：按渠道/支付方式汇总导出",
        ],
    ),
    Module(
        id="marketing",
        title="营销与分析（Marketing & BI）",
        summary="活动规则与多维报表看板",
        checklist=[
            "活动规则（最小集）：满减/折扣/券（可按门店/类目/会员等级）",
            "报表与看板：销售额、客单价、UPT、毛利（估）、TOPN 商品/时段热力",
            "门店/区域多维透视：store_id 分区 + 物化视图刷新（分钟级）",
        ],
    ),
    Module(
        id="system",
        title="系统（System）",
        summary="用户权限、任务与审计日志",
        checklist=[
            "用户/角色/权限、API 密钥、审计日志（谁在何时做了什么）",
            "任务：导入任务、批处理、定时刷新",
            "用户登录和验证",
        ],
    ),
]


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
        return RedirectResponse(url="/web/dashboard", status_code=status.HTTP_303_SEE_OTHER)
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
    response = RedirectResponse(url="/web/dashboard", status_code=status.HTTP_303_SEE_OTHER)
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


@router.get("/", include_in_schema=False)
def index(request: Request, db: Session = Depends(get_db)):
    """Redirect to dashboard or login depending on session."""
    user = _current_user(request, db)
    target = "/web/dashboard" if user else "/web/login"
    return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login?error=login_required", status_code=status.HTTP_303_SEE_OTHER)
    active_module = request.query_params.get("module") or _MODULES[0].id
    module_ids = {module.id for module in _MODULES}
    if active_module not in module_ids:
        active_module = _MODULES[0].id
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "modules": _MODULES,
            "active_module": active_module,
            "current_user": user,
        },
    )


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
