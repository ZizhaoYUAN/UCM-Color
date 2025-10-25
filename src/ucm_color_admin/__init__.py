"""UCM Color Admin packaged backend service."""

from importlib.metadata import PackageNotFoundError, version

try:  # pragma: no cover - handled at runtime
    __version__ = version("ucm-color-admin")
except PackageNotFoundError:  # pragma: no cover - local execution before install
    __version__ = "0.2.0"

__all__ = ["__version__"]
