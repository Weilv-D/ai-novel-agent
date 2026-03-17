#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."

# Playwright re用固定 SQLite 文件；启动前清掉旧库，避免历史 schema 污染当前用例。
rm -f e2e_test.db e2e_test.db-shm e2e_test.db-wal

exec ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8001}"
