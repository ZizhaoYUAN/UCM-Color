#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DIST_DIR="$ROOT_DIR/dist"
INSTALLER_ROOT="$DIST_DIR/installers"
TEMPLATE_DIR="$ROOT_DIR/installer"

rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR" "$INSTALLER_ROOT"

python -m build --outdir "$DIST_DIR"

VERSION=$(python - <<'PY'
import pathlib
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback
    import tomli as tomllib  # type: ignore

data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
print(data["project"]["version"])
PY
)

PKG_PREFIX="ucm-color-admin-$VERSION"
TARGET_DIR="$INSTALLER_ROOT/$PKG_PREFIX"
mkdir -p "$TARGET_DIR"

WHEEL=$(ls "$DIST_DIR"/ucm_color_admin-*.whl | head -n 1)
cp "$WHEEL" "$TARGET_DIR"/
cp "$TEMPLATE_DIR"/install.sh "$TARGET_DIR"/
cp "$TEMPLATE_DIR"/install.ps1 "$TARGET_DIR"/
cp "$TEMPLATE_DIR"/README.txt "$TARGET_DIR"/
chmod +x "$TARGET_DIR"/install.sh

# Create archives for distribution
( cd "$INSTALLER_ROOT" && tar -czf "$PKG_PREFIX-linux-macos.tar.gz" "$PKG_PREFIX" )
python - <<PY
import pathlib
import zipfile

installer_dir = pathlib.Path("$INSTALLER_ROOT")
prefix = "$PKG_PREFIX"
zip_path = installer_dir / f"{prefix}-windows.zip"
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in (installer_dir / prefix).rglob("*"):
        archive.write(path, path.relative_to(installer_dir))
PY

echo "Installer artifacts created under $INSTALLER_ROOT"
