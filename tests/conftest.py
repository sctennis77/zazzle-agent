import os
os.environ["STRIPE_SECRET_KEY"] = "test_secret_key"

import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pytest_plugins = ["pytest_asyncio"]

# Patch StripeService before any imports to prevent initialization errors
mock_stripe_service = MagicMock()

# Configure the mock to return real donation objects
def save_donation_to_db_side_effect(db, payment_intent_data, donation_request):
    from app.db.models import Donation, Subreddit
    from app.models import DonationStatus, get_tier_from_amount
    
    # Check if donation already exists
    existing_donation = db.query(Donation).filter_by(
        stripe_payment_intent_id=payment_intent_data["payment_intent_id"]
    ).first()
    
    if existing_donation:
        return existing_donation
    
    # Get or create subreddit
    subreddit_id = None
    if donation_request.subreddit:
        subreddit = db.query(Subreddit).filter_by(subreddit_name=donation_request.subreddit).first()
        if not subreddit:
            subreddit = Subreddit(
                subreddit_name=donation_request.subreddit,
                display_name=donation_request.subreddit.title()
            )
            db.add(subreddit)
            db.commit()
            db.refresh(subreddit)
        subreddit_id = subreddit.id
    
    # Determine tier
    tier = get_tier_from_amount(donation_request.amount_usd)
    
    # Create donation
    donation = Donation(
        stripe_payment_intent_id=payment_intent_data["payment_intent_id"],
        amount_cents=payment_intent_data["amount_cents"],
        amount_usd=payment_intent_data["amount_usd"],
        currency="usd",
        status=DonationStatus.PENDING.value,
        tier=tier.value,
        customer_email=donation_request.customer_email,
        customer_name=donation_request.customer_name,
        message=donation_request.message,
        subreddit_id=subreddit_id,
        reddit_username=donation_request.reddit_username,
        is_anonymous=donation_request.is_anonymous,
        stripe_metadata=payment_intent_data.get("metadata", {}),
        donation_type=donation_request.donation_type,
        commission_type=donation_request.commission_type,
        post_id=donation_request.post_id,
        commission_message=donation_request.commission_message,
    )
    
    db.add(donation)
    db.commit()
    db.refresh(donation)
    return donation

def update_donation_status_side_effect(db, payment_intent_id, status):
    from app.db.models import Donation
    donation = db.query(Donation).filter_by(stripe_payment_intent_id=payment_intent_id).first()
    if donation:
        donation.status = status.value
        db.commit()
        db.refresh(donation)
    return donation

def process_subreddit_tiers_side_effect(db, donation):
    # Mock implementation - just return empty dict
    return {}

# Configure the mock methods
mock_stripe_service.save_donation_to_db.side_effect = save_donation_to_db_side_effect
mock_stripe_service.update_donation_status.side_effect = update_donation_status_side_effect
mock_stripe_service.process_subreddit_tiers.side_effect = process_subreddit_tiers_side_effect

# Apply the patch at module level
patch("app.api.stripe_service", mock_stripe_service).start()


@pytest.fixture(autouse=True, scope="session")
def patch_database():
    """Patch all database-related imports to use test database and create schema from models."""
    import os
    from app.db.models import Base

    # Set testing environment variable
    os.environ["TESTING"] = "true"

    # Create a test engine using a file-based database to avoid threading issues
    test_db_path = Path("/tmp/test_zazzle_agent.db")
    test_engine = create_engine(f"sqlite:///{test_db_path}")
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create all tables from models
    Base.metadata.create_all(bind=test_engine)

    # Patch the app's database engine/session to use the test DB
    with (
        patch("app.db.database.get_database_url", return_value=f"sqlite:///{test_db_path}"),
        patch("app.db.database.engine", test_engine),
        patch("app.db.database.SessionLocal", TestSessionLocal),
        # Also patch the get_db function to use our test session
        patch("app.db.database.get_db", lambda: TestSessionLocal()),
    ):
        # Store the test session for use in other fixtures
        patch_database.test_session = TestSessionLocal
        yield
    
    # Cleanup: remove the test database file
    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture(autouse=True, scope="session")
def patch_stripe_service():
    """Patch StripeService to prevent initialization errors during tests."""
    yield mock_stripe_service


@pytest.fixture(scope="session")
def test_data():
    """Create basic test data for donation tests."""
    from app.db.models import Subreddit, PipelineRun, RedditPost
    from datetime import datetime, timezone

    # Use the same session that was used for migrations
    db = patch_database.test_session()
    
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
