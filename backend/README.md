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

- Python 3.11+
- Docker & Docker Compose

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

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
```

### Code Quality

```bash
# Linting
ruff check app/

# Formatting
ruff format app/

# Type checking
mypy app/
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
