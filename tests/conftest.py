import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(autouse=True, scope="session")
def patch_database():
    """Patch all database-related imports to use in-memory database for tests and run Alembic migrations."""
    import os
    from alembic.config import Config
    from alembic import command

    # Set testing environment variable
    os.environ["TESTING"] = "true"

    # Create a test engine and session
    test_engine = create_engine("sqlite:///:memory:")
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Patch the app's database engine/session to use the test DB
    with (
        patch("app.db.database.get_database_url", return_value="sqlite:///:memory:"),
        patch("app.db.database.engine", test_engine),
        patch("app.db.database.SessionLocal", TestSessionLocal),
    ):
        # Run Alembic migrations against the in-memory test DB
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", "sqlite:///:memory:")
        command.upgrade(alembic_cfg, "head")
        yield


@pytest.fixture(scope="session")
def test_data():
    """Create basic test data for donation tests."""
    from app.db.database import SessionLocal
    from app.db.models import Subreddit, PipelineRun, RedditPost
    from datetime import datetime, timezone

    db = SessionLocal()
    
    # Create a test subreddit
    subreddit = Subreddit(
        subreddit_name="test",
        display_name="Test Subreddit",
        description="A test subreddit for donation tests",
        subscribers=100,
        over18=False,
        spoilers_enabled=False,
    )
    db.add(subreddit)
    db.commit()
    db.refresh(subreddit)

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
        version="1.0.0"
    )
    db.add(pipeline_run)
    db.commit()
    db.refresh(pipeline_run)

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
        num_comments=5
    )
    db.add(reddit_post)
    db.commit()
    db.refresh(reddit_post)

    yield subreddit, pipeline_run, reddit_post
    db.close()


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
