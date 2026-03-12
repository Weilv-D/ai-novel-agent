#!/bin/bash
# Initialize database with migrations

set -e

echo "Running database migrations..."
alembic upgrade head

echo "Creating pgvector extension..."
python -c "
import asyncio
from app.db.init_db import create_pgvector_extension
asyncio.run(create_pgvector_extension())
"

echo "Database initialized successfully!"
