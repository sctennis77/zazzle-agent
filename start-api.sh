#!/bin/bash

# API Startup Script
set -e

echo "🔧 Initializing database..."

# TEMPORARY: Drop and recreate database schema since we have no production data
# TODO: Remove this once migration issues are resolved
echo "⚠️  TEMPORARY: Dropping existing schema for fresh migration..."
timeout 30 python -c "
import sys
from sqlalchemy import create_engine, text, MetaData
from app.db.database import get_database_url

try:
    print('🔗 Connecting to database...')
    engine = create_engine(get_database_url(), connect_args={'connect_timeout': 10})
    
    with engine.connect() as conn:
        print('📋 Reflecting database metadata...')
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        print(f'📊 Found {len(metadata.tables)} tables to drop')
        if len(metadata.tables) > 0:
            print('🗑️  Dropping tables...')
            metadata.drop_all(bind=engine)
            print('✅ All tables dropped')
        else:
            print('ℹ️  No tables to drop')
        
        # Drop alembic_version table specifically
        try:
            conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
            conn.commit()
            print('✅ Alembic version table dropped')
        except Exception as e:
            print(f'ℹ️  Alembic table: {e}')
            
except Exception as e:
    print(f'❌ Database operation failed: {e}')
    print('🔄 Continuing with migration anyway...')
" || echo "⚠️  Database drop timed out or failed, continuing with migration..."

echo "🔄 Applying fresh migration..."
python -m alembic upgrade head

echo "🚀 Starting API server..."
exec uvicorn app.api:app --host 0.0.0.0 --port ${PORT:-8000} 