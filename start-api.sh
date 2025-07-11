#!/bin/bash

# API Startup Script
set -e

echo "🔧 Initializing database..."
python -m alembic upgrade head

echo "🚀 Starting API server..."
exec uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000} 