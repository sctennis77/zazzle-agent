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

    def test_commission_payment_to_task_creation(
        self, db_session, mock_stripe_service, mock_payment_intent, test_subreddit
    ):
        """Test that successful payment creates a commission task."""
        
        # Mock the Stripe service to create a realistic donation
        def mock_save_donation(db, payment_data, request_data):
            donation = Donation(
                stripe_payment_intent_id=payment_data["payment_intent_id"],
                amount_cents=payment_data["amount_cents"],
                amount_usd=payment_data["amount_usd"],
                currency="usd",
                status=DonationStatus.PENDING.value,
                tier=DonationTier.COMMISSION.value,
                customer_email="commissioner@test.com",
                customer_name="Test Commissioner",
                message="Create something amazing from a hiking post!",
                subreddit_id=test_subreddit.id,
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
                result = handle_payment_intent_succeeded(db_session, mock_payment_intent)

            # Verify donation was created
            donation = db_session.query(Donation).filter_by(
                stripe_payment_intent_id="pi_test_commission_123"
            ).first()
            
            assert donation is not None
            assert donation.amount_usd == 25.00
            assert donation.commission_type == "random_subreddit"
            assert donation.subreddit_id == test_subreddit.id

            # Verify task creation was attempted
            mock_task_manager.create_commission_task.assert_called_once()

    def test_commission_task_processing(self, db_session, test_subreddit):
        """Test commission task processing creates pipeline run and task."""
        
        # Create a test donation
        donation = Donation(
            stripe_payment_intent_id="pi_test_processing_123",
            amount_cents=2500,
            amount_usd=25.00,
            currency="usd",
            status=DonationStatus.SUCCEEDED.value,
            tier=DonationTier.COMMISSION.value,
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
        
        with patch.object(task_manager, '_create_pipeline_run') as mock_create_run:
            with patch.object(task_manager, '_create_pipeline_task') as mock_create_task:
                # Mock return values
                mock_pipeline_run = PipelineRun(
                    id=1,
                    status="running",
                    start_time=datetime.now(timezone.utc),
                    summary="Commission pipeline run",
                    config={"commission": True},
                    metrics={},
                    duration=0,
                    retry_count=0,
                    version="1.0.0"
                )
                mock_create_run.return_value = mock_pipeline_run
                
                mock_task = PipelineTask(
                    id=1,
                    task_type="commission",
                    status="pending",
                    pipeline_run_id=1,
                    subreddit_id=test_subreddit.id,
                    message="Make something cool!",
                    commission_type="random_subreddit",
                    donation_id=donation.id
                )
                mock_create_task.return_value = mock_task

                # Execute task creation
                pipeline_run, task = task_manager.create_commission_task(
                    db_session, donation
                )

                # Verify task creation
                assert pipeline_run is not None
                assert task is not None
                assert task.commission_type == "random_subreddit"
                assert task.donation_id == donation.id

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
            tier=DonationTier.COMMISSION.value,
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
            task_type="commission",
            status="pending",
            pipeline_run_id=pipeline_run.id,
            subreddit_id=test_subreddit.id,
            message="Create a hiking-themed product",
            commission_type="random_subreddit",
            donation_id=donation.id
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Step 3: Mock product generation
        with patch("app.agents.reddit_agent.RedditAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent
            
            # Mock successful product creation
            from app.models import ProductInfo
            mock_product = ProductInfo(
                theme="Mountain Adventure",
                product_url="https://zazzle.com/mountain_product",
                image_url="https://example.com/mountain.jpg",
                template_id="hiking_template",
                model="dall-e-3",
                prompt_version="1.0.0",
                product_type="t-shirt",
                design_description="Beautiful mountain landscape"
            )
            mock_agent._find_and_create_product_for_task = AsyncMock(return_value=mock_product)

            # Step 4: Process the task
            from app.commission_worker import CommissionWorker
            worker = CommissionWorker()
            
            with patch.object(worker, '_publish_to_subreddit') as mock_publish:
                mock_publish.return_value = True
                
                result = await worker.process_commission_task(db_session, task)
                
                # Verify successful processing
                assert result is True
                
                # Verify the agent was called
                mock_agent._find_and_create_product_for_task.assert_called_once_with(
                    db_session, task
                )

    def test_commission_validation_workflow(self, db_session, test_subreddit):
        """Test commission validation before processing."""
        from app.services.commission_validator import CommissionValidator
        
        # Create valid commission
        valid_donation = Donation(
            stripe_payment_intent_id="pi_valid_123",
            amount_cents=2500,
            amount_usd=25.00,
            currency="usd",
            status=DonationStatus.SUCCEEDED.value,
            tier=DonationTier.COMMISSION.value,
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
        is_valid, reason = validator.validate_commission(valid_donation)
        assert is_valid is True
        assert reason is None

        # Test invalid commission (no subreddit)
        invalid_donation = Donation(
            stripe_payment_intent_id="pi_invalid_123",
            amount_cents=1000,  # Too low
            amount_usd=10.00,
            currency="usd",
            status=DonationStatus.SUCCEEDED.value,
            tier=DonationTier.BASIC.value,  # Wrong tier
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
        
        is_valid, reason = validator.validate_commission(invalid_donation)
        assert is_valid is False
        assert reason is not None