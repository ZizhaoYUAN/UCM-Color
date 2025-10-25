from functools import lru_cache
from typing import List

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    app_name: str = "Retail Admin API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default="sqlite:///./retail.db",
        env="DB__CONN",
        description="SQLAlchemy compatible database URL",
    )
    echo_sql: bool = Field(default=False, env="DB__ECHO")
    default_page_size: int = 50
    max_page_size: int = 200
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    enable_seed_data: bool = Field(default=True, env="APP__SEED_DATA")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
