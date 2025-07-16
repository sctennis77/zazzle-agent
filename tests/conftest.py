"""
Centralized test configuration and fixtures.

This module provides a unified approach to test setup, database management,
and common fixtures to eliminate duplication across test files.
"""

import os
import shutil
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Set test environment variables early
os.environ["TESTING"] = "true"
os.environ["STRIPE_SECRET_KEY"] = "test_secret_key"
os.environ["STRIPE_WEBHOOK_SECRET"] = "test_webhook_secret"
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
        f"sqlite:///{test_db_path}", connect_args={"check_same_thread": False}
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
    redis_mock = MagicMock()
    redis_mock.stop_listening = AsyncMock()
    redis_mock.disconnect = AsyncMock()

    monkeypatch.setattr("app.redis_service.redis", MagicMock())
    monkeypatch.setattr("app.websocket_manager.redis_service", redis_mock)
    monkeypatch.setattr(
        "app.services.background_scheduler.BackgroundScheduler", MagicMock()
    )

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
    mock_response.choices[0].message.content = (
        '{"theme": "Test Theme", "description": "Test description"}'
    )
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


@pytest.fixture
def test_data(db_session):
    """Create basic test data for donation tests."""
    from datetime import datetime, timezone

    from app.db.models import PipelineRun, RedditPost, Subreddit

    # Create a test subreddit
    subreddit = Subreddit(
        subreddit_name="test",
        display_name="Test Subreddit",
        description="A test subreddit for donation tests",
        subscribers=100,
        over18=False,
        spoilers_enabled=False,
    )
    db_session.add(subreddit)
    db_session.commit()
    db_session.refresh(subreddit)

    # Create a test pipeline run
    pipeline_run = PipelineRun(
        status="completed",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        summary="Test pipeline run completed",
        config={"test": True},
        metrics={"products_generated": 1},
        duration=10,
        retry_count=0,
        version="1.0.0",
    )
    db_session.add(pipeline_run)
    db_session.commit()
    db_session.refresh(pipeline_run)

    # Create a test Reddit post
    reddit_post = RedditPost(
        post_id="test_post_id_abc",
        title="Test Post Title",
        content="Test post content for donation tests.",
        subreddit_id=subreddit.id,
        score=10,
        url="https://reddit.com/r/test/comments/test_post_id_abc",
        permalink="/r/test/comments/test_post_id_abc/test_post_title/",
        pipeline_run_id=pipeline_run.id,
        comment_summary="Test comment summary",
        author="test_user",
        num_comments=5,
    )
    db_session.add(reddit_post)
    db_session.commit()
    db_session.refresh(reddit_post)

    return subreddit, pipeline_run, reddit_post


@pytest.fixture
def db(db_session):
    """Alias for db_session for compatibility."""
    return db_session


@pytest.fixture
def sample_subreddit(db_session):
    """Create a sample subreddit for tests."""
    from app.db.models import Subreddit

    subreddit = Subreddit(
        subreddit_name="test",
        display_name="Test Subreddit",
        description="A test subreddit",
        subscribers=100,
        over18=False,
        spoilers_enabled=False,
    )
    db_session.add(subreddit)
    db_session.commit()
    db_session.refresh(subreddit)
    return subreddit


@pytest.fixture
def sample_commission_donation(db, sample_subreddit):
    """Create a sample commission donation."""
    import uuid

    from app.db.models import Donation
    from app.models import DonationStatus

    unique_intent_id = f"pi_test_{uuid.uuid4().hex[:8]}"
    donation = Donation(
        customer_name="Test User",
        customer_email="test@example.com",
        amount_usd=25.0,
        amount_cents=2500,
        currency="usd",
        status=DonationStatus.SUCCEEDED.value,
        tier="sapphire",
        stripe_payment_intent_id=unique_intent_id,
        subreddit_id=sample_subreddit.id,
        donation_type="commission",
        commission_type="random_subreddit",
        commission_message="Test commission message",
        is_anonymous=False,
        reddit_username="testuser",
        post_id="test_post_123",
        stripe_metadata={"test": "data"},
    )
    db.add(donation)
    db.commit()
    db.refresh(donation)
    return donation


@pytest.fixture
def sample_failed_task(db, sample_commission_donation, sample_subreddit):
    """Create a sample failed task for tests."""
    from app.db.models import PipelineTask

    task = PipelineTask(
        task_type="commission",
        status="failed",
        subreddit_id=sample_subreddit.id,
        donation_id=sample_commission_donation.id,
        message="Test task message",
        commission_type="random_subreddit",
        error_message="Test error message",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@pytest.fixture
def task_manager():
    """Create a task manager for tests."""
    from app.task_manager import TaskManager

    return TaskManager()


@pytest.fixture
def sample_fundraising_goal(db_session, sample_subreddit):
    """Create a sample fundraising goal for tests."""
    from datetime import datetime, timezone

    from app.db.models import SubredditFundraisingGoal

    goal = SubredditFundraisingGoal(
        subreddit_id=sample_subreddit.id,
        goal_amount=100.00,
        current_amount=0.00,
        goal_description="Test fundraising goal",
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc),
        is_active=True,
    )
    db_session.add(goal)
    db_session.commit()
    db_session.refresh(goal)
    return goal
