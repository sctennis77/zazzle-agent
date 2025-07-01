#!/usr/bin/env python3
"""
Script to create a fresh database with the new simplified tier system.
This will drop all existing data and recreate the schema from scratch.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.db.database import Base
from app.db.models import *  # Import all models
from app.db.database import get_database_url

def create_fresh_database():
    """Create a fresh database with the new schema."""
    
    # Get database URL
    database_url = get_database_url()
    
    # Create engine
    engine = create_engine(database_url)
    
    print("Dropping all existing tables...")
    
    # Drop all tables
    Base.metadata.drop_all(engine)
    
    print("Creating new tables with simplified schema...")
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    print("Database recreated successfully!")
    print(f"Database URL: {database_url}")
    
    # Test the connection
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result.fetchall()]
        print(f"Created tables: {tables}")

if __name__ == "__main__":
    print("Creating fresh database with simplified tier system...")
    create_fresh_database()
    print("Done!") 