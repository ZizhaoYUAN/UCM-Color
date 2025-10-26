"""Pydantic schemas for API payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    full_name: Optional[str] = Field(None, max_length=128)
    email: Optional[EmailStr] = None
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=128)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class DownloadEntry(BaseModel):
    """Metadata returned for downloadable installer archives."""

    filename: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1)
    size: int = Field(..., ge=0)
