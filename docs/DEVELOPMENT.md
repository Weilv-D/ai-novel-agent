# Development Guide

## Working Environments

This repository currently uses these local environments:

- `backend/.venv`: the active Python environment for backend development and tests
- `frontend/node_modules`: the active frontend dependency environment
- `backend/.env`: local backend runtime settings
- `frontend/.env.local`: local frontend runtime settings

The repository root `/.venv` is not used by the project and can be treated as disposable.

## Backend

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/alembic upgrade head
./.venv/bin/python verify.py
./.venv/bin/python -m pytest
./.venv/bin/ruff check app tests
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Notes:

- Run backend commands from `backend/` so `app.core.config.Settings` can resolve `.env`.
- Tests intentionally isolate themselves from developer-local `backend/.env` values.
- PostgreSQL + pgvector is the target runtime. SQLite is used only for tests and lightweight verification.
- The app runs in single-user mode. `PERSONAL_USER_EMAIL` / `PERSONAL_USER_NAME` define ownership, and `ADMIN_API_KEY` is an optional access gate for browser/API usage. The frontend will auto-discover the configured `API_KEY_HEADER` from `/api/v1/health`.

## Frontend

```bash
cd frontend
npm install
npm run lint
npm run build
npm run dev
```

Notes:

- Next.js config lives in `frontend/next.config.mjs`.
- Frontend scripts call the local Next.js CLI through `node`, so they do not depend on executable bits inside `node_modules/.bin`.

## Common Commands

At the repository root:

```bash
make backend-test
make backend-lint
make backend-typecheck
make backend-verify
make frontend-build
make frontend-lint
make verify
make clean
```

`make verify` runs the complete local quality gate: backend lint, backend typecheck, backend tests, frontend lint, and frontend build. `make clean` removes generated caches, the disposable root `/.venv`, and the frontend build output. It does not remove `backend/.venv`, `frontend/node_modules`, or local `.env` files.
