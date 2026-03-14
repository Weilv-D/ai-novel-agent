#!/bin/bash
# Start script for AI Novel Agent local development

set -e

echo "=================================================="
echo "  AI Novel Agent - Local Development Startup"
echo "=================================================="
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed."
    echo "Please install Docker Compose first."
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
docker-compose up -d

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
echo "  docker-compose logs -f [service]"
echo ""
echo "To stop services:"
echo "  docker-compose down"
echo ""
echo "To verify API integration:"
echo "  cd ../backend && python scripts/verify_api_integration.py"
echo ""
