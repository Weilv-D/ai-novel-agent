#!/bin/bash
# Start script for AI Novel Agent local development

set -e

echo "=================================================="
echo "  AI Novel Agent - Local Development Startup"
echo "=================================================="
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Resolve Docker Compose command (supports v1 and v2)
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD=(docker-compose)
elif docker compose version &> /dev/null; then
    COMPOSE_CMD=(docker compose)
else
    echo "Error: Docker Compose is not installed."
    echo "Install either 'docker-compose' or the 'docker compose' plugin first."
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "Error: Docker is not running."
    echo "Please start Docker first."
    exit 1
fi

echo "Starting all services with Docker Compose..."
echo ""

# Start services
"${COMPOSE_CMD[@]}" up -d

echo ""
echo "=================================================="
echo "  Services are starting..."
echo "=================================================="
echo ""
echo "  Backend API:    http://localhost:8000"
echo "  Frontend App:   http://localhost:3000"
echo "  API Docs:       http://localhost:8000/docs"
echo "  PostgreSQL:     localhost:5432"
echo "  Redis:          localhost:6379"
echo ""
echo "To view logs:"
echo "  ${COMPOSE_CMD[*]} logs -f [service]"
echo ""
echo "To stop services:"
echo "  ${COMPOSE_CMD[*]} down"
echo ""
echo "To run the backend test suite:"
echo "  cd ../backend && ./.venv/bin/python -m pytest"
echo ""
