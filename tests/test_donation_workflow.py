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
from app.db.models import Donation, Sponsor, SponsorTier, SubredditFundraisingGoal, PipelineTask
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
def sample_sponsor_tier():
    """Create a sample sponsor tier."""
    db = SessionLocal()
    try:
        tier = SponsorTier(
            name="Bronze",
            min_amount=Decimal('5.00'),
            benefits="Basic sponsor benefits",
            description="Entry level sponsorship"
        )
        db.add(tier)
        db.commit()
        db.refresh(tier)
        return tier
    finally:
        db.close()


@pytest.fixture
def sample_fundraising_goal():
    """Create a sample fundraising goal."""
    db = SessionLocal()
    try:
        goal = SubredditFundraisingGoal(
            subreddit="test_subreddit",
            goal_amount=Decimal('100.00'),
            current_amount=Decimal('0.00'),
            status="active"
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return goal
    finally:
        db.close()


def test_donation_creates_sponsor_and_task(stripe_service, sample_sponsor_tier):
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
            is_anonymous=False
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
        
        # Check that sponsor was created
        sponsor = db.query(Sponsor).filter_by(donation_id=donation.id).first()
        assert sponsor is not None
        assert sponsor.tier_id == sample_sponsor_tier.id
        assert sponsor.subreddit == "test_subreddit"
        assert sponsor.status == "active"
        
        # Check that pipeline task was created
        task = db.query(PipelineTask).filter_by(sponsor_id=sponsor.id).first()
        assert task is not None
        assert task.type == "SUBREDDIT_POST"
        assert task.subreddit == "test_subreddit"
        assert task.priority == 10  # Higher priority for sponsor tasks
        assert task.status == "pending"
        assert task.context_data["donation_id"] == donation.id
        assert task.context_data["donation_amount"] == 10.0
        assert task.context_data["sponsor_tier"] == "Bronze"
        assert task.context_data["customer_name"] == "Test User"
        assert task.context_data["is_anonymous"] is False
        
    finally:
        db.close()


def test_donation_updates_fundraising_goal(stripe_service, sample_sponsor_tier):
    """Test that a donation updates fundraising goal progress."""
    db = SessionLocal()
    try:
        # Create a fundraising goal in the same session
        goal = SubredditFundraisingGoal(
            subreddit="test_subreddit",
            goal_amount=Decimal('100.00'),
            current_amount=Decimal('0.00'),
            status="active"
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        
        # Create a donation request
        donation_request = DonationRequest(
            amount_usd=Decimal('10.00'),  # Match sponsor tier minimum
            customer_email="test@example.com",
            customer_name="Test User",
            subreddit="test_subreddit",
            reddit_username="testuser",
            is_anonymous=False
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
        
        # Check that fundraising goal was updated
        db.refresh(goal)
        assert goal.current_amount == Decimal('10.00')
        assert goal.status == "active"  # Not completed yet
        
    finally:
        db.close()


def test_donation_completes_fundraising_goal(stripe_service, sample_sponsor_tier):
    """Test that a donation can complete a fundraising goal."""
    db = SessionLocal()
    try:
        # Create a fundraising goal in the same session
        goal = SubredditFundraisingGoal(
            subreddit="test_subreddit",
            goal_amount=Decimal('100.00'),
            current_amount=Decimal('0.00'),
            status="active"
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        
        # Create a donation request that exceeds the goal
        donation_request = DonationRequest(
            amount_usd=Decimal('150.00'),
            customer_email="test@example.com",
            customer_name="Test User",
            subreddit="test_subreddit",
            reddit_username="testuser",
            is_anonymous=False
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
        
        # Check that fundraising goal was completed
        db.refresh(goal)
        assert goal.current_amount == Decimal('150.00')
        assert goal.status == "completed"
        assert goal.completed_at is not None
        
    finally:
        db.close()


def test_anonymous_donation_workflow(stripe_service, sample_sponsor_tier):
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
            is_anonymous=True
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
        
        # Check that sponsor was created
        sponsor = db.query(Sponsor).filter_by(donation_id=donation.id).first()
        assert sponsor is not None
        
        # Check that pipeline task was created with anonymous context
        task = db.query(PipelineTask).filter_by(sponsor_id=sponsor.id).first()
        assert task is not None
        assert task.context_data["is_anonymous"] is True
        assert task.context_data["customer_name"] == "Anonymous"
        
    finally:
        db.close() 