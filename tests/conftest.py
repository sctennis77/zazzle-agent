import pytest
from unittest.mock import patch
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(autouse=True, scope="session")
def patch_database():
    """Patch all database-related imports to use in-memory database for tests."""
    # Create a test engine and session
    test_engine = create_engine('sqlite:///:memory:')
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    with patch("app.db.database.get_database_url", return_value="sqlite:///:memory:"), \
         patch("app.db.database.engine", test_engine), \
         patch("app.db.database.SessionLocal", TestSessionLocal):
        yield

@pytest.fixture(scope="session")
def test_output_dir(tmp_path_factory):
    """Create a temporary directory for test outputs."""
    test_dir = tmp_path_factory.mktemp("test_outputs")
    yield test_dir
    # Cleanup after all tests are done
    shutil.rmtree(test_dir)

@pytest.fixture(autouse=True)
def set_test_output_dir(test_output_dir, monkeypatch):
    """Automatically set the test output directory for all tests."""
    # Override the default outputs directory for tests
    monkeypatch.setenv("OUTPUT_DIR", str(test_output_dir))
    # Create necessary subdirectories
    (test_output_dir / "screenshots").mkdir(exist_ok=True)
    (test_output_dir / "images").mkdir(exist_ok=True)
    return test_output_dir 