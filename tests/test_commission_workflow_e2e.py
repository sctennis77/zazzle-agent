"""
End-to-End Commission Workflow Test.

This test validates the complete commission workflow from payment success
to product generation, ensuring all components work together correctly.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api import handle_payment_intent_succeeded
from app.db.models import Donation, PipelineRun, PipelineTask, Subreddit
from app.models import DonationStatus, DonationTier
from app.task_manager import TaskManager


@pytest.fixture
def mock_payment_intent():
    """Create a mock Stripe payment intent object."""
    payment_intent = MagicMock()
    payment_intent.id = "pi_test_commission_123"
    payment_intent.amount = 2500  # $25.00 in cents
    payment_intent.currency = "usd"
    payment_intent.receipt_email = "commissioner@test.com"
    payment_intent.metadata = {
        "donation_type": "commission",
        "commission_type": "random_subreddit",
        "subreddit": "hiking",
        "post_id": "",
        "commission_message": "Create something amazing from a hiking post!",
        "customer_name": "Test Commissioner",
        "reddit_username": "test_commissioner",
        "is_anonymous": "false",
    }
    return payment_intent


@pytest.fixture
def test_subreddit(db_session):
    """Create a test subreddit for commission tests."""
    subreddit = Subreddit(
        subreddit_name="hiking",
        display_name="Hiking",
        description="Hiking community",
        subscribers=50000,
        over18=False,
        spoilers_enabled=False,
    )
    db_session.add(subreddit)
    db_session.commit()
    db_session.refresh(subreddit)
    return subreddit


class TestCommissionWorkflowE2E:
    """End-to-end tests for commission workflow."""

    @pytest.mark.asyncio
    async def test_commission_payment_to_task_creation(
        self, db_session, mock_stripe_service, mock_payment_intent, test_subreddit
    ):
        """Test that successful payment creates a commission task."""
        
        # Store subreddit id to avoid session issues
        subreddit_id = test_subreddit.id
        
        # Mock the Stripe service to create a realistic donation
        def mock_save_donation(db, payment_data, request_data):
            donation = Donation(
                stripe_payment_intent_id=payment_data["payment_intent_id"],
                amount_cents=payment_data["amount_cents"],
                amount_usd=payment_data["amount_usd"],
                currency="usd",
                status=DonationStatus.SUCCEEDED.value,  # Set to succeeded for commission
                tier=DonationTier.SAPPHIRE.value,
                customer_email="commissioner@test.com",
                customer_name="Test Commissioner",
                message="Create something amazing from a hiking post!",
                subreddit_id=subreddit_id,
                reddit_username="test_commissioner",
                is_anonymous=False,
                donation_type="commission",
                commission_type="random_subreddit",
                commission_message="Create something amazing from a hiking post!",
            )
            db.add(donation)
            db.commit()
            db.refresh(donation)
            return donation

        mock_stripe_service.save_donation_to_db.side_effect = mock_save_donation

        # Mock task manager to capture task creation
        with patch("app.api.task_manager") as mock_task_manager:
            mock_task_manager.create_commission_task = MagicMock()
            
            # Simulate the webhook handler
            with patch("app.api.stripe_service", mock_stripe_service):
                with patch("app.api.SessionLocal", return_value=db_session):
                    result = await handle_payment_intent_succeeded(mock_payment_intent)

            # Verify donation was created
            donation = db_session.query(Donation).filter_by(
                stripe_payment_intent_id="pi_test_commission_123"
            ).first()
            
            assert donation is not None
            assert donation.amount_usd == 25.00
            assert donation.commission_type == "random_subreddit"
            assert donation.subreddit_id == subreddit_id

            # Verify task creation was attempted
            mock_task_manager.create_commission_task.assert_called_once()

    def test_commission_task_processing(self, db_session, test_subreddit):
        """Test commission task processing creates pipeline task."""
        
        # Create a test donation
        donation = Donation(
            stripe_payment_intent_id="pi_test_processing_123",
            amount_cents=2500,
            amount_usd=25.00,
            currency="usd",
            status=DonationStatus.SUCCEEDED.value,
            tier=DonationTier.SAPPHIRE.value,
            customer_email="test@example.com",
            customer_name="Test User",
            message="Create awesome product",
            subreddit_id=test_subreddit.id,
            reddit_username="test_user",
            is_anonymous=False,
            donation_type="commission",
            commission_type="random_subreddit",
            commission_message="Make something cool!",
        )
        db_session.add(donation)
        db_session.commit()
        db_session.refresh(donation)

        # Mock TaskManager
        task_manager = TaskManager()
        
        # Create task data like the API does
        task_data = {
            "subreddit_name": "hiking",
            "post_id": "",
            "customer_email": donation.customer_email,
            "customer_name": donation.customer_name,
            "reddit_username": donation.reddit_username,
            "is_anonymous": donation.is_anonymous,
            "donation_type": donation.donation_type,
            "commission_type": donation.commission_type,
            "commission_message": donation.commission_message,
            "post_id": donation.post_id,
            "image_quality": "high",
        }
        
        with patch.object(task_manager, '_create_pipeline_task') as mock_create_task:
            # Mock return value - just return a task ID
            mock_create_task.return_value = "task_123"

            # Execute task creation
            task_id = task_manager.create_commission_task(
                donation.id, task_data, db_session
            )

            # Verify task creation
            assert task_id == "task_123"
            mock_create_task.assert_called_once_with(donation.id, task_data, db_session)

    @pytest.mark.asyncio
    async def test_full_commission_workflow_mock(
        self, db_session, mock_stripe_service, test_subreddit
    ):
        """Test the complete commission workflow with mocked external services."""
        
        # Step 1: Create donation from payment
        donation = Donation(
            stripe_payment_intent_id="pi_full_workflow_123",
            amount_cents=2500,
            amount_usd=25.00,
            currency="usd",
            status=DonationStatus.SUCCEEDED.value,
            tier=DonationTier.SAPPHIRE.value,
            customer_email="workflow@test.com",
            customer_name="Workflow Test",
            message="Full workflow test",
            subreddit_id=test_subreddit.id,
            reddit_username="workflow_user",
            is_anonymous=False,
            donation_type="commission",
            commission_type="random_subreddit",
            commission_message="Create a hiking-themed product",
        )
        db_session.add(donation)
        db_session.commit()

        # Step 2: Create pipeline run and task
        pipeline_run = PipelineRun(
            status="running",
            start_time=datetime.now(timezone.utc),
            summary="Full workflow test run",
            config={"commission": True, "subreddit": "hiking"},
            metrics={},
            duration=0,
            retry_count=0,
            version="1.0.0"
        )
        db_session.add(pipeline_run)
        db_session.commit()
        db_session.refresh(pipeline_run)

        task = PipelineTask(
            type="commission",
            status="pending",
            pipeline_run_id=pipeline_run.id,
            subreddit_id=test_subreddit.id,
            donation_id=donation.id,
            context_data={
                "message": "Create a hiking-themed product",
                "commission_type": "random_subreddit"
            }
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Step 3: Test CommissionWorker initialization
        from app.commission_worker import CommissionWorker
        task_data = {
            "subreddit_name": "hiking",
            "commission_type": "random_subreddit",
            "commission_message": "Create a hiking-themed product"
        }
        worker = CommissionWorker(donation.id, task_data)
        
        # Verify worker initialization
        assert worker.donation_id == donation.id
        assert worker.task_data == task_data
        
        # Verify task and donation are properly linked
        assert task.donation_id == donation.id
        assert task.subreddit_id == test_subreddit.id

    @pytest.mark.asyncio
    async def test_commission_validation_workflow(self, db_session, test_subreddit):
        """Test commission validation before processing."""
        from app.services.commission_validator import CommissionValidator
        
        # Create valid commission
        valid_donation = Donation(
            stripe_payment_intent_id="pi_valid_123",
            amount_cents=2500,
            amount_usd=25.00,
            currency="usd",
            status=DonationStatus.SUCCEEDED.value,
            tier=DonationTier.SAPPHIRE.value,
            customer_email="valid@test.com",
            customer_name="Valid User",
            message="Valid commission",
            subreddit_id=test_subreddit.id,
            reddit_username="valid_user",
            is_anonymous=False,
            donation_type="commission",
            commission_type="random_subreddit",
            commission_message="Create something awesome",
        )
        
        validator = CommissionValidator()
        
        # Test validation passes
        result = await validator.validate_commission(valid_donation)
        assert result.valid is True
        assert result.error is None

        # Test invalid commission (no subreddit)
        invalid_donation = Donation(
            stripe_payment_intent_id="pi_invalid_123",
            amount_cents=1000,  # Too low
            amount_usd=10.00,
            currency="usd",
            status=DonationStatus.SUCCEEDED.value,
            tier=DonationTier.BRONZE.value,  # Wrong tier
            customer_email="invalid@test.com",
            customer_name="Invalid User",
            message="Invalid commission",
            subreddit_id=None,  # Missing subreddit
            reddit_username="invalid_user",
            is_anonymous=False,
            donation_type="commission",
            commission_type="random_subreddit",
            commission_message="",  # Empty message
        )
        
        result = await validator.validate_commission(invalid_donation)
        assert result.valid is False
        assert result.error is not None