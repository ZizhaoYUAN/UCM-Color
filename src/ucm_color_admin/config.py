"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


@dataclass(slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    app_name: str = field(default_factory=lambda: os.environ.get("UCM_COLOR_APP_NAME", "UCM Color Admin"))
    host: str = field(default_factory=lambda: os.environ.get("UCM_COLOR_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.environ.get("UCM_COLOR_PORT", "8000")))
    reload: bool = field(default_factory=lambda: os.environ.get("UCM_COLOR_RELOAD", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.environ.get("UCM_COLOR_LOG_LEVEL", "info"))
    database_path: Path = field(
        default_factory=lambda: Path(os.environ.get("UCM_COLOR_DB", "~/.ucm_color_admin/database.sqlite3")).expanduser()
    )
    installer_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("UCM_COLOR_INSTALLER_DIR", "~/.ucm_color_admin/installers")).expanduser()
    )

    def ensure_storage(self) -> None:
        """Ensure that the database directory exists."""

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.installer_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    settings = Settings()
    settings.ensure_storage()
    return settings
