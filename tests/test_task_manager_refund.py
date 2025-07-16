"""
Tests for TaskManager refund functionality.

This module tests the automatic refund handling when commission tasks fail.
"""

import uuid
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.db.models import Donation, PipelineTask, Subreddit
from app.services.stripe_service import StripeService
from app.task_manager import TaskManager, TaskStatus


class TestTaskManagerRefund:
    """Test TaskManager refund functionality."""

    @pytest.fixture
    def task_manager(self):
        """Create a TaskManager instance."""
        return TaskManager()

    @pytest.fixture
    def sample_subreddit(self, db):
        """Create a sample subreddit with a unique name per test."""
        unique_name = f"test_subreddit_{uuid.uuid4().hex[:8]}"
        subreddit = Subreddit(subreddit_name=unique_name, display_name="Test Subreddit")
        db.add(subreddit)
        db.commit()
        db.refresh(subreddit)
        return subreddit

    @pytest.fixture
    def sample_commission_donation(self, db, sample_subreddit):
        """Create a sample commission donation."""
        unique_intent_id = f"pi_test_{uuid.uuid4().hex[:8]}"
        donation = Donation(
            customer_name="Test User",
            customer_email="test@example.com",
            amount_usd=25.0,
            amount_cents=2500,
            donation_type="commission",
            tier="platinum",
            status="succeeded",
            stripe_payment_intent_id=unique_intent_id,
            reddit_username="testuser",
            is_anonymous=False,
            commission_type="custom",
            commission_message="Test commission",
            subreddit_id=sample_subreddit.id,
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)
        return donation

    @pytest.fixture
    def sample_failed_task(self, db, sample_commission_donation, sample_subreddit):
        """Create a sample failed commission task."""
        task = PipelineTask(
            type="SUBREDDIT_POST",
            donation_id=sample_commission_donation.id,
            subreddit_id=sample_subreddit.id,
            status=TaskStatus.FAILED.value,
            error_message="Commission processing failed",
            context_data={"test": "data"},
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def test_handle_failed_commission_refund_success(
        self, task_manager, db, sample_failed_task
    ):
        """Test successful refund for failed commission task."""
        with patch.object(StripeService, "refund_payment_intent") as mock_refund:
            mock_refund.return_value = {
                "refund_id": "re_test_123",
                "amount_refunded": 25.0,
                "status": "refunded",
                "customer_email": "test@example.com",
            }
            task_manager._handle_failed_commission_refund(
                db, sample_failed_task, "Test error"
            )
            # Use the actual payment intent ID from the fixture
            mock_refund.assert_called_once_with(
                db,
                sample_failed_task.donation.stripe_payment_intent_id,
                "Commission failed: Test error",
            )

    def test_handle_failed_commission_refund_no_donation(
        self, task_manager, db, sample_subreddit
    ):
        """Test refund handling when no donation is found."""
        task = PipelineTask(
            type="SUBREDDIT_POST",
            donation_id=None,  # No donation
            subreddit_id=sample_subreddit.id,
            status=TaskStatus.FAILED.value,
            error_message="Test error",
        )

        with patch.object(StripeService, "refund_payment_intent") as mock_refund:
            task_manager._handle_failed_commission_refund(db, task, "Test error")

            # Verify Stripe service was not called
            mock_refund.assert_not_called()

    def test_handle_failed_commission_refund_non_commission_donation(
        self, task_manager, db, sample_subreddit
    ):
        """Test refund handling for non-commission donations."""
        # Create a non-commission donation
        donation = Donation(
            customer_name="Test User",
            customer_email="test@example.com",
            amount_usd=10.0,
            amount_cents=1000,
            donation_type="donation",  # Not commission
            tier="bronze",
            status="succeeded",
            stripe_payment_intent_id="pi_test_456",
            subreddit_id=sample_subreddit.id,
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)

        task = PipelineTask(
            type="SUBREDDIT_POST",
            donation_id=donation.id,
            subreddit_id=sample_subreddit.id,
            status=TaskStatus.FAILED.value,
            error_message="Test error",
        )
        db.add(task)
        db.commit()

        with patch.object(StripeService, "refund_payment_intent") as mock_refund:
            task_manager._handle_failed_commission_refund(db, task, "Test error")

            # Verify Stripe service was not called
            mock_refund.assert_not_called()

    def test_handle_failed_commission_refund_no_stripe_payment(
        self, task_manager, db, sample_subreddit
    ):
        """Test refund handling for donations without Stripe payment."""
        # Create a commission donation with empty Stripe payment intent ID
        donation = Donation(
            customer_name="Test User",
            customer_email="test@example.com",
            amount_usd=15.0,
            amount_cents=1500,
            donation_type="commission",
            tier="silver",
            status="succeeded",
            stripe_payment_intent_id="",  # Empty string instead of None
            subreddit_id=sample_subreddit.id,
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)

        task = PipelineTask(
            type="SUBREDDIT_POST",
            donation_id=donation.id,
            subreddit_id=sample_subreddit.id,
            status=TaskStatus.FAILED.value,
            error_message="Test error",
        )
        db.add(task)
        db.commit()

        with patch.object(StripeService, "refund_payment_intent") as mock_refund:
            task_manager._handle_failed_commission_refund(db, task, "Test error")

            # Verify Stripe service was not called
            mock_refund.assert_not_called()

    def test_handle_failed_commission_refund_already_refunded(
        self, task_manager, db, sample_subreddit
    ):
        """Test refund handling for already refunded donations."""
        # Create an already refunded donation
        donation = Donation(
            customer_name="Test User",
            customer_email="test@example.com",
            amount_usd=20.0,
            amount_cents=2000,
            donation_type="commission",
            tier="gold",
            status="refunded",  # Already refunded
            stripe_payment_intent_id="pi_test_789",
            subreddit_id=sample_subreddit.id,
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)

        task = PipelineTask(
            type="SUBREDDIT_POST",
            donation_id=donation.id,
            subreddit_id=sample_subreddit.id,
            status=TaskStatus.FAILED.value,
            error_message="Test error",
        )
        db.add(task)
        db.commit()

        with patch.object(StripeService, "refund_payment_intent") as mock_refund:
            task_manager._handle_failed_commission_refund(db, task, "Test error")

            # Verify Stripe service was not called
            mock_refund.assert_not_called()

    def test_handle_failed_commission_refund_failed_payment(
        self, task_manager, db, sample_subreddit
    ):
        """Test refund handling for failed payments."""
        # Create a failed payment donation
        donation = Donation(
            customer_name="Test User",
            customer_email="test@example.com",
            amount_usd=30.0,
            amount_cents=3000,
            donation_type="commission",
            tier="platinum",
            status="failed",  # Failed payment
            stripe_payment_intent_id="pi_test_101",
            subreddit_id=sample_subreddit.id,
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)

        task = PipelineTask(
            type="SUBREDDIT_POST",
            donation_id=donation.id,
            subreddit_id=sample_subreddit.id,
            status=TaskStatus.FAILED.value,
            error_message="Test error",
        )
        db.add(task)
        db.commit()

        with patch.object(StripeService, "refund_payment_intent") as mock_refund:
            task_manager._handle_failed_commission_refund(db, task, "Test error")

            # Verify Stripe service was not called
            mock_refund.assert_not_called()

    def test_handle_failed_commission_refund_stripe_error(
        self, task_manager, db, sample_failed_task
    ):
        """Test refund handling when Stripe service fails."""
        with patch.object(StripeService, "refund_payment_intent") as mock_refund:
            mock_refund.return_value = None  # Stripe service failed
            task_manager._handle_failed_commission_refund(
                db, sample_failed_task, "Test error"
            )
            # Verify Stripe service was called
            mock_refund.assert_called_once()

    def test_handle_failed_commission_refund_exception_handling(
        self, task_manager, db, sample_failed_task
    ):
        """Test exception handling in refund process."""
        with patch.object(StripeService, "refund_payment_intent") as mock_refund:
            mock_refund.side_effect = Exception("Stripe API error")
            # Should not raise exception
            task_manager._handle_failed_commission_refund(
                db, sample_failed_task, "Test error"
            )
            # Verify Stripe service was called
            mock_refund.assert_called_once()

    def test_handle_task_failure_triggers_refund(
        self, task_manager, db, sample_failed_task
    ):
        """Test that handle_task_failure triggers refund for commission tasks."""
        with patch.object(
            task_manager, "_handle_failed_commission_refund"
        ) as mock_refund:
            task_manager.handle_task_failure(db, sample_failed_task.id, "Test error")

            # Verify refund was called
            mock_refund.assert_called_once_with(db, sample_failed_task, "Test error")

    def test_handle_task_failure_no_task_found(self, task_manager, db):
        """Test handle_task_failure when task is not found."""
        with patch.object(
            task_manager, "_handle_failed_commission_refund"
        ) as mock_refund:
            task_manager.handle_task_failure(db, 99999, "Test error")

            # Verify refund was not called
            mock_refund.assert_not_called()

    def test_update_task_status_triggers_refund_on_failure(
        self, task_manager, db, sample_commission_donation, sample_subreddit
    ):
        """Test that updating task status to failed triggers refund."""
        # Create a task with status 'pending'
        task = PipelineTask(
            type="SUBREDDIT_POST",
            donation_id=sample_commission_donation.id,
            subreddit_id=sample_subreddit.id,
            status=TaskStatus.PENDING.value,
            error_message=None,
            context_data={"test": "data"},
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        with patch("app.task_manager.SessionLocal", return_value=db):
            with patch.object(
                task_manager, "_handle_failed_commission_refund"
            ) as mock_refund:
                task_manager._update_task_status(task.id, "failed", "Test error")
                # Verify refund was called
                mock_refund.assert_called()

    def test_update_task_status_no_refund_on_success(
        self, task_manager, db, sample_failed_task
    ):
        """Test that updating task status to completed does not trigger refund."""
        with patch.object(
            task_manager, "_handle_failed_commission_refund"
        ) as mock_refund:
            task_manager._update_task_status(str(sample_failed_task.id), "completed")

            # Verify refund was not called
            mock_refund.assert_not_called()
