#!/bin/sh
set -eu

PYTHON_USER_BASE="${PYTHON_USER_BASE:-/tmp/ai-novel-agent-python}"
DEPS_STAMP_FILE="${DEPS_STAMP_FILE:-/tmp/ai-novel-agent-requirements.sha256}"

export PYTHONUSERBASE="$PYTHON_USER_BASE"
export PATH="$PYTHON_USER_BASE/bin:$PATH"

mkdir -p "$PYTHON_USER_BASE"

CURRENT_DEPS_HASH="$(sha256sum requirements.txt | awk '{print $1}')"
STORED_DEPS_HASH=""

if [ -f "$DEPS_STAMP_FILE" ]; then
  STORED_DEPS_HASH="$(cat "$DEPS_STAMP_FILE")"
fi

DEPS_OK="1"
if ! python - <<'PY' >/dev/null 2>&1
import importlib

for module_name in ("fastapi", "sqlalchemy", "asyncpg", "docx"):
    importlib.import_module(module_name)
PY
then
  DEPS_OK="0"
fi

if [ "$CURRENT_DEPS_HASH" != "$STORED_DEPS_HASH" ] || [ "$DEPS_OK" != "1" ]; then
  echo "Synchronizing backend Python dependencies..."
  python -m pip install --user --no-cache-dir -r requirements.txt
  printf '%s' "$CURRENT_DEPS_HASH" > "$DEPS_STAMP_FILE"
fi

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
