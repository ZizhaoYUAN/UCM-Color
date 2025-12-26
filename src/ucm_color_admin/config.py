"""Application configuration helpers."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


def _default_data_root() -> Path:
    """Return the platform specific directory used for persistent data."""

    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        return base / "UCMColorAdmin"
    return Path.home() / ".ucm_color_admin"


def _default_database_path() -> Path:
    """Resolve the database path taking overrides into account."""

    override = os.environ.get("UCM_COLOR_DB")
    if override:
        return Path(override).expanduser()
    return _default_data_root() / "database.sqlite3"


def _default_installer_dir() -> Path:
    """Resolve the installer directory taking overrides into account."""

    override = os.environ.get("UCM_COLOR_INSTALLER_DIR")
    if override:
        return Path(override).expanduser()
    return _default_data_root() / "installers"


def _default_secret_key() -> str:
    """Return the secret key used for signing sessions."""

    override = os.environ.get("UCM_COLOR_SECRET")
    if override:
        return override
    return secrets.token_hex(32)


@dataclass(slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    app_name: str = field(default_factory=lambda: os.environ.get("UCM_COLOR_APP_NAME", "UCM Color Admin"))
    host: str = field(default_factory=lambda: os.environ.get("UCM_COLOR_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.environ.get("UCM_COLOR_PORT", "8000")))
    reload: bool = field(default_factory=lambda: os.environ.get("UCM_COLOR_RELOAD", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.environ.get("UCM_COLOR_LOG_LEVEL", "info"))
    database_path: Path = field(default_factory=_default_database_path)
    installer_dir: Path = field(default_factory=_default_installer_dir)
    secret_key: str = field(default_factory=_default_secret_key)

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
