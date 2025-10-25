from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Message(BaseModel):
    message: str


class Pagination(BaseModel):
    total: int
    limit: int
    offset: int


class Timestamped(BaseModel):
    created_at: datetime
    updated_at: Optional[datetime] | None = None
