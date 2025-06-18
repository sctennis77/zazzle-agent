#!/usr/bin/env python3

from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

print("Testing enhanced database URL patching...")

# Create a test engine and session
test_engine = create_engine('sqlite:///:memory:')
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Test the enhanced patching
with patch("app.db.database.get_database_url", return_value="sqlite:///:memory:"), \
     patch("app.db.database.engine", test_engine), \
     patch("app.db.database.SessionLocal", TestSessionLocal):
    
    from app.db.database import get_database_url, engine, SessionLocal
    print(f"Patched URL: {get_database_url()}")
    print(f"Patched engine URL: {engine.url}")
    print(f"Patched SessionLocal: {SessionLocal}")
    
    # Test that we can create a session
    session = SessionLocal()
    print(f"Test session created: {session}")
    session.close()

print("Enhanced patching test complete!") 