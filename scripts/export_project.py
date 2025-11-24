#!/usr/bin/env python3
"""Create a cleaned project archive for distribution."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import zipfile


DEFAULT_EXCLUDES = {
    ".git",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    ".venv",
}

DEFAULT_EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log",
    ".tmp",
}


def _should_exclude(path: Path, root: Path, include_git: bool) -> bool:
    """Return ``True`` when *path* should be omitted from the archive."""

    if path == root:
        return False

    relative = path.relative_to(root)

    # Skip directories explicitly listed in the exclude set.
    parts = set(relative.parts)
    excluded_parts = DEFAULT_EXCLUDES - ({".git"} if include_git else set())
    if excluded_parts & parts:
        return True

    # Skip Python cache files and other temporary artefacts.
    if relative.suffix in DEFAULT_EXCLUDE_EXTENSIONS:
        return True

    return False


def create_archive(output: Path, include_git: bool) -> Path:
    """Create the project archive at *output* and return the generated path."""

    root = Path(__file__).resolve().parents[1]
    project_root_name = root.name

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if _should_exclude(path, root, include_git):
                continue
            archive.write(path, Path(project_root_name) / path.relative_to(root))

    return output


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Destination path for the archive. Defaults to dist/<project>.zip",
    )
    parser.add_argument(
        "--include-git",
        action="store_true",
        help="Include the .git directory in the generated archive.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    root = Path(__file__).resolve().parents[1]
    default_output = root / "dist" / f"{root.name}.zip"
    output = args.output or default_output

    archive = create_archive(output, include_git=args.include_git)
    print(f"Archive written to {archive}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
