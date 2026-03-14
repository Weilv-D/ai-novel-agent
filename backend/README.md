# AI Novel Agent Backend

FastAPI backend for the AI Novel Agent project. The backend is already beyond “skeleton” stage: CRUD APIs, agent routes, memory search, snapshots, dependency analysis, export, and test coverage are all present.

This backend now targets a practical personal-use mode: one fixed local user owns all projects, with optional API key protection on application endpoints.

## Current Validation Snapshot

- `398` tests collected
- `396 passed`, `2 skipped`
- `ruff check app tests` passes with the current repository rule set
- `mypy app` passes with the current repository rule set
- `verify.py` still works as a quick import/OpenAPI sanity check
- `scripts/verify_sqlite_integration.py` passes end-to-end against temporary SQLite
- `scripts/verify_api_integration.py` passes against the live Docker-backed backend

## Local Setup

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
./.venv/bin/alembic upgrade head
```

Run commands from `backend/` so `app.core.config.Settings` can resolve `.env` correctly.

## Common Commands

```bash
# quick verification
./.venv/bin/python verify.py

# tests
./.venv/bin/python -m pytest
./.venv/bin/python -m pytest tests/test_integration/test_http_integration.py -v

# lint / type check
./.venv/bin/ruff check app tests
./.venv/bin/python -m mypy app

# local server
./.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# full repository verification
cd ..
make verify
```

## Runtime Notes

- Production target is PostgreSQL 16 + pgvector.
- Tests use SQLite and custom compatibility fixtures to stay isolated from local developer settings.
- `EMBEDDING_DIMENSION` must match the selected embedding model output size.
- `PERSONAL_USER_EMAIL` / `PERSONAL_USER_NAME` define the local single-user identity.
- `ADMIN_API_KEY` is optional. When set, all data/agent/export routes require that value in the configured `API_KEY_HEADER`.
- Startup now initializes the personal user record automatically after migrations.

## Scripts

- `verify.py`: quick backend sanity checks
- `scripts/verify_api_integration.py`: manual live-backend smoke test
- `scripts/verify_sqlite_integration.py`: manual SQLite-backed HTTP smoke test
- `scripts/start_dev.sh`: runs Alembic migrations, then starts the development server

The old standalone SQLite migration test script has been removed. The maintained path is the pytest integration suite in `tests/test_integration/test_sqlite_migration.py`.

## Structure

```text
backend/
├── app/
│   ├── agents/
│   ├── api/v1/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   └── services/
├── alembic/
├── scripts/
├── tests/
├── pyproject.toml
└── verify.py
```

## API Docs

Once the server is running:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/api/v1/health`
