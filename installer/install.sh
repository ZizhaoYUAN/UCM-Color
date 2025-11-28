#!/usr/bin/env bash
set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=${PYTHON:-python3}
else
    PYTHON_BIN=${PYTHON:-python}
fi

INSTALL_DIR=${1:-"$HOME/.local/share/ucm-color-admin"}
mkdir -p "$INSTALL_DIR"

VENV_DIR="$INSTALL_DIR/venv"
"$PYTHON_BIN" -m venv "$VENV_DIR"

VENV_PY="$VENV_DIR/bin/python"
"$VENV_PY" -m pip install --upgrade pip

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
WHEEL_PATH=$(ls "$SCRIPT_DIR"/ucm_color_admin-*.whl 2>/dev/null | head -n 1 || true)
if [[ -z "$WHEEL_PATH" ]]; then
    echo "Unable to locate the installer wheel." >&2
    exit 1
fi

"$VENV_PY" -m pip install "$WHEEL_PATH"

LAUNCHER="$INSTALL_DIR/ucm-color-admin.sh"
cat <<'LAUNCH' > "$LAUNCHER"
#!/usr/bin/env bash
DIR=$(cd "$(dirname "$0")" && pwd)
exec "$DIR/venv/bin/ucm-color-admin" "$@"
LAUNCH
chmod +x "$LAUNCHER"

echo "Installation complete."
echo "Run '$LAUNCHER run' to start the server."
