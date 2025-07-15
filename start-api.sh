#!/bin/bash

# API Startup Script
set -e

echo "🔧 Initializing database..."

# TEMPORARY: Drop and recreate database schema since we have no production data
# TODO: Remove this once migration issues are resolved
echo "⚠️  TEMPORARY: Dropping existing schema for fresh migration..."
python -c "
from sqlalchemy import create_engine, text, MetaData
from app.db.database import get_database_url

engine = create_engine(get_database_url())
with engine.connect() as conn:
    # Drop all tables
    metadata = MetaData()
    metadata.reflect(bind=engine)
    metadata.drop_all(bind=engine)
    print('✅ All tables dropped')
    
    # Drop alembic_version table specifically if it exists
    try:
        conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
        conn.commit()
        print('✅ Alembic version table dropped')
    except:
        print('ℹ️  Alembic version table not found (already clean)')
"

echo "🔄 Applying fresh migration..."
python -m alembic upgrade head

echo "🚀 Starting API server..."
exec uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000} 