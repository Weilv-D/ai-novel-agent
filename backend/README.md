# AI Novel Agent Backend

Backend service for AI Novel Agent - a long-form novel writing system with agent-based AI collaboration.

## Tech Stack

- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL 16 + pgvector
- **Cache**: Redis
- **Task Queue**: Celery
- **LLM**: OpenAI SDK (compatible)

## Development Setup

### Prerequisites

**Option 1: Full Docker Setup (Recommended)**
- Docker & Docker Compose
- No Python installation required

**Option 2: Local Python Setup**
- Python 3.11+
- pip and venv module
- PostgreSQL 16 + pgvector (for full features)
- Redis (for caching/celery)

> **Note**: The `verify.py` script and basic tests require Python dependencies to be installed.

### Quick Start (No Database Required)

```bash
# Install dependencies
pip install -e ".[dev]"

# Run verification to check installation
python verify.py

# Run tests (uses SQLite, no external dependencies)
pytest

# Start development server (health endpoint works without database)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Full Local Development (with PostgreSQL)

```bash
# Start services with Docker Compose
cd ../infra && docker-compose up -d

# Run database migrations
alembic upgrade head

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_health.py -v
```

**Database Note**: Tests use SQLite for isolation and speed. SQLite is sufficient for unit/integration tests, but production requires PostgreSQL 16 + pgvector for full feature support (vector similarity search, JSONB, native UUID).

### Code Quality

```bash
# Linting
ruff check app/

# Formatting
ruff format app/

# Type checking
mypy app/
```

## Project Structure

```
backend/
├── app/
│   ├── api/v1/          # API routes
│   │   └── health.py    # Health check endpoint (no DB required)
│   ├── core/            # Configuration, logging, security
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic (to be implemented)
│   ├── agents/          # Agent orchestration (to be implemented)
│   ├── db/              # Database session management
│   └── main.py          # FastAPI entry point
├── tests/               # Test suite (uses SQLite for isolation)
│   ├── conftest.py      # Pytest configuration
│   └── test_api/        # API tests
├── alembic/             # Database migrations
│   └── versions/        # Migration files
├── scripts/             # Utility scripts
├── pyproject.toml       # Project configuration
└── verify.py            # Quick verification script
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/api/v1/health

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Current Status

Phase 1 (Backend Skeleton) - In Progress
- ✅ Project structure and configuration
- ✅ All SQLAlchemy models defined
- ✅ Health check API endpoint (no DB dependency)
- ✅ Initial Alembic migration
- ✅ Basic test suite with isolated tests
- ✅ Docker Compose setup (postgres, redis, backend services)
- ⏳ LLM service integration
