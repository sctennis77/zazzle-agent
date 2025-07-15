#!/bin/bash

# API Startup Script
set -e

echo "🔧 Initializing database..."

# Check if alembic_version table exists and has incompatible revision
if python -c "
import os
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
try:
    with engine.connect() as conn:
        result = conn.execute(text('SELECT version_num FROM alembic_version'))
        version = result.fetchone()
        if version and version[0] != '687b4d7540f4':
            print('NEEDS_RESET')
        else:
            print('OK')
except:
    print('OK')
" | grep -q "NEEDS_RESET"; then
    echo "⚠️  Detected incompatible migration history. Resetting to fresh schema..."
    python -c "
from sqlalchemy import create_engine, text
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
with engine.connect() as conn:
    conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
    conn.commit()
    print('Reset complete')
"
fi

python -m alembic upgrade head

echo "🚀 Starting API server..."
exec uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000} 