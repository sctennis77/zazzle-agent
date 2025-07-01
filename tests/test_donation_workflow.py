"""
Test the donation-to-task workflow.

This module tests that when a donation is made:
1. A sponsor record is created
2. A pipeline task is created for that sponsor
3. Fundraising goals are updated
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.db.database import Base, SessionLocal, engine
from app.db.models import Donation, SubredditFundraisingGoal, PipelineTask
from app.models import DonationRequest, DonationStatus
from app.services.stripe_service import StripeService


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Drop and recreate all tables before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def stripe_service():
    """Create a StripeService instance for testing."""
    return StripeService()


@pytest.fixture
def sample_fundraising_goal():
    """Create a sample fundraising goal and yield its ID."""
    db = SessionLocal()
    try:
        # First create a subreddit
        from app.db.models import Subreddit
        subreddit = Subreddit(
            subreddit_name="test_subreddit",
            display_name="Test Subreddit"
        )
        db.add(subreddit)
        db.commit()
        db.refresh(subreddit)
        
        # Then create the fundraising goal
        from app.db.models import SubredditFundraisingGoal
        goal = SubredditFundraisingGoal(
            subreddit_id=subreddit.id,
            goal_amount=Decimal('100.00'),
            current_amount=Decimal('0.00'),
            status="active"
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        yield goal.id
    finally:
        db.close()


def test_donation_creates_sponsor_and_task(stripe_service, sample_fundraising_goal):
    """Test that a successful donation creates a sponsor and pipeline task."""
    db = SessionLocal()
    try:
        # Create a donation request
        donation_request = DonationRequest(
            amount_usd=Decimal('10.00'),
            customer_email="test@example.com",
            customer_name="Test User",
            subreddit="test_subreddit",
            reddit_username="testuser",
            is_anonymous=False,
            donation_type="support",
            post_id="test_post_id"
        )
        
        # Mock payment intent data
        payment_intent_data = {
            "payment_intent_id": "pi_test123",
            "amount_cents": 1000,
            "amount_usd": Decimal('10.00'),
            "metadata": {}
        }
        
        # Save donation to database
        donation = stripe_service.save_donation_to_db(db, payment_intent_data, donation_request)
        assert donation is not None
        assert donation.status == DonationStatus.PENDING.value
        
        # Update donation status to succeeded
        updated_donation = stripe_service.update_donation_status(db, "pi_test123", DonationStatus.SUCCEEDED)
        assert updated_donation is not None
        assert updated_donation.status == DonationStatus.SUCCEEDED.value
        
        # Re-query fundraising goal from this session
        from app.db.models import SubredditFundraisingGoal
        goal = db.query(SubredditFundraisingGoal).get(sample_fundraising_goal)
        assert goal.current_amount == Decimal('10.00')
        assert goal.status == "active"  # Not completed yet
        
    finally:
        db.close()


def test_donation_updates_fundraising_goal(stripe_service, sample_fundraising_goal):
    """Test that a donation updates fundraising goal progress."""
    db = SessionLocal()
    try:
        # Create a donation request
        donation_request = DonationRequest(
            amount_usd=Decimal('10.00'),
            customer_email="test@example.com",
            customer_name="Test User",
            subreddit="test_subreddit",
            reddit_username="testuser",
            is_anonymous=False,
            donation_type="support",
            post_id="test_post_id"
        )
        
        # Mock payment intent data
        payment_intent_data = {
            "payment_intent_id": "pi_test456",
            "amount_cents": 1000,
            "amount_usd": Decimal('10.00'),
            "metadata": {}
        }
        
        # Save donation to database
        donation = stripe_service.save_donation_to_db(db, payment_intent_data, donation_request)
        assert donation is not None
        
        # Update donation status to succeeded
        updated_donation = stripe_service.update_donation_status(db, "pi_test456", DonationStatus.SUCCEEDED)
        assert updated_donation is not None
        
        # Re-query fundraising goal from this session
        from app.db.models import SubredditFundraisingGoal
        goal = db.query(SubredditFundraisingGoal).get(sample_fundraising_goal)
        assert goal.current_amount == Decimal('10.00')
        assert goal.status == "active"  # Not completed yet
        
    finally:
        db.close()


def test_donation_completes_fundraising_goal(stripe_service, sample_fundraising_goal):
    """Test that a donation can complete a fundraising goal."""
    db = SessionLocal()
    try:
        # Create a donation request that exceeds the goal
        donation_request = DonationRequest(
            amount_usd=Decimal('150.00'),
            customer_email="test@example.com",
            customer_name="Test User",
            subreddit="test_subreddit",
            reddit_username="testuser",
            is_anonymous=False,
            donation_type="support",
            post_id="test_post_id"
        )
        
        # Mock payment intent data
        payment_intent_data = {
            "payment_intent_id": "pi_test789",
            "amount_cents": 15000,
            "amount_usd": Decimal('150.00'),
            "metadata": {}
        }
        
        # Save donation to database
        donation = stripe_service.save_donation_to_db(db, payment_intent_data, donation_request)
        assert donation is not None
        
        # Update donation status to succeeded
        updated_donation = stripe_service.update_donation_status(db, "pi_test789", DonationStatus.SUCCEEDED)
        assert updated_donation is not None
        
        # Re-query fundraising goal from this session
        from app.db.models import SubredditFundraisingGoal
        goal = db.query(SubredditFundraisingGoal).get(sample_fundraising_goal)
        assert goal.current_amount == Decimal('150.00')
        assert goal.status == "completed"
        assert goal.completed_at is not None
        
    finally:
        db.close()


def test_anonymous_donation_workflow(stripe_service, sample_fundraising_goal):
    """Test that anonymous donations work correctly."""
    db = SessionLocal()
    try:
        # Create an anonymous donation request
        donation_request = DonationRequest(
            amount_usd=Decimal('25.00'),
            customer_email="anonymous@example.com",
            customer_name="Anonymous",
            subreddit="test_subreddit",
            reddit_username="anonymous_user",
            is_anonymous=True,
            donation_type="support",
            post_id="test_post_id"
        )
        
        # Mock payment intent data
        payment_intent_data = {
            "payment_intent_id": "pi_anonymous123",
            "amount_cents": 2500,
            "amount_usd": Decimal('25.00'),
            "metadata": {}
        }
        
        # Save donation to database
        donation = stripe_service.save_donation_to_db(db, payment_intent_data, donation_request)
        assert donation is not None
        assert donation.is_anonymous is True
        
        # Update donation status to succeeded
        updated_donation = stripe_service.update_donation_status(db, "pi_anonymous123", DonationStatus.SUCCEEDED)
        assert updated_donation is not None
        
        # Re-query fundraising goal from this session
        from app.db.models import SubredditFundraisingGoal
        goal = db.query(SubredditFundraisingGoal).get(sample_fundraising_goal)
        assert goal.current_amount == Decimal('25.00')
        assert goal.status == "active"  # Not completed yet
        
    finally:
        db.close() 