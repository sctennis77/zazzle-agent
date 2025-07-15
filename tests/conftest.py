"""
Centralized test configuration and fixtures.

This module provides a unified approach to test setup, database management,
and common fixtures to eliminate duplication across test files.
"""

import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test environment variables early
os.environ["TESTING"] = "true"
os.environ["STRIPE_SECRET_KEY"] = "test_secret_key"
os.environ["ADMIN_SECRET"] = "testsecret123"

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine for the entire test session."""
    from app.db.models import Base
    
    # Use a file-based SQLite database for thread safety
    test_db_path = "/tmp/zazzle_test_session.db"
    
    # Clean up any existing test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    engine.dispose()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Create a session factory for tests."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    """
    Provide a clean database session for each test.
    
    Each test gets a fresh transaction that is rolled back at the end,
    ensuring test isolation without recreating the database schema.
    """
    from sqlalchemy.orm import sessionmaker
    
    connection = test_engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(bind=connection)
    session = TestSession()
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def mock_stripe_service():
    """Provide a mock Stripe service with minimal necessary functionality."""
    mock_service = MagicMock()
    
    # Simple mock implementations that don't duplicate business logic
    mock_service.save_donation_to_db.return_value = MagicMock(id=1)
    mock_service.update_donation_status.return_value = MagicMock(id=1)
    mock_service.process_subreddit_tiers.return_value = {}
    
    return mock_service


@pytest.fixture
def client(db_session, mock_stripe_service, monkeypatch):
    """Create a FastAPI test client with database and service overrides."""
    from fastapi.testclient import TestClient
    
    # Mock Redis and other external services to prevent connection attempts
    monkeypatch.setattr("app.redis_service.redis", MagicMock())
    monkeypatch.setattr("app.websocket_manager.redis_service", MagicMock())
    monkeypatch.setattr("app.services.background_scheduler.BackgroundScheduler", MagicMock())
    
    # Import app after patching external dependencies
    from app.api import app, get_db
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    
    with patch("app.api.stripe_service", mock_stripe_service):
        with TestClient(app) as test_client:
            yield test_client
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def test_output_dir(tmp_path_factory):
    """Create a temporary directory for test outputs."""
    test_dir = tmp_path_factory.mktemp("test_outputs")
    yield test_dir
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def setup_test_environment(test_output_dir, monkeypatch):
    """Automatically configure test environment for all tests."""
    # Set up output directories
    monkeypatch.setenv("OUTPUT_DIR", str(test_output_dir))
    
    # Create necessary subdirectories
    (test_output_dir / "screenshots").mkdir(exist_ok=True)
    (test_output_dir / "images").mkdir(exist_ok=True)
    
    return test_output_dir


@pytest.fixture
def sample_subreddit_data():
    """Provide sample subreddit data for tests."""
    return {
        "subreddit_name": "test",
        "display_name": "Test Subreddit",
        "description": "A test subreddit",
        "subscribers": 100,
        "over18": False,
        "spoilers_enabled": False,
    }


@pytest.fixture
def sample_reddit_post_data():
    """Provide sample Reddit post data for tests."""
    return {
        "post_id": "test_post_123",
        "title": "Test Post Title",
        "content": "Test post content",
        "score": 42,
        "url": "https://reddit.com/r/test/comments/test_post_123",
        "permalink": "/r/test/comments/test_post_123/test_post_title/",
        "author": "test_user",
        "num_comments": 5,
    }


@pytest.fixture
def mock_openai_client():
    """Provide a mock OpenAI client for tests."""
    mock_client = MagicMock()
    
    # Mock chat completion
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"theme": "Test Theme", "description": "Test description"}'
    mock_client.chat.completions.create.return_value = mock_response
    
    # Mock image generation
    mock_image_response = MagicMock()
    mock_image_response.data[0].url = "https://example.com/test-image.jpg"
    mock_client.images.generate.return_value = mock_image_response
    
    return mock_client


@pytest.fixture
def mock_reddit_client():
    """Provide a mock Reddit (PRAW) client for tests."""
    mock_reddit = MagicMock()
    
    # Mock subreddit
    mock_subreddit = MagicMock()
    mock_subreddit.display_name = "test"
    mock_subreddit.subscribers = 100
    mock_reddit.subreddit.return_value = mock_subreddit
    
    # Mock submission
    mock_submission = MagicMock()
    mock_submission.id = "test_post_123"
    mock_submission.title = "Test Post"
    mock_submission.selftext = "Test content"
    mock_submission.score = 42
    mock_submission.num_comments = 5
    mock_submission.author.name = "test_user"
    mock_submission.subreddit.display_name = "test"
    mock_submission.url = "https://reddit.com/test"
    mock_submission.permalink = "/r/test/test"
    
    mock_subreddit.hot.return_value = [mock_submission]
    mock_subreddit.new.return_value = [mock_submission]
    
    return mock_reddit