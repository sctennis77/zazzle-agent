from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.db.models import Donation, Subreddit
from app.models import DonationRequest, DonationStatus
from app.services.stripe_service import StripeService


class TestStripeRefund:
    """Test cases for Stripe refund functionality."""

    @pytest.fixture
    def stripe_service(self):
        """Create a StripeService instance for testing."""
        return StripeService()

    @pytest.fixture
    def sample_donation(self, db: Session):
        """Create a sample donation for testing."""
        import uuid

        # Get or create subreddit
        subreddit = db.query(Subreddit).filter_by(subreddit_name="programming").first()
        if not subreddit:
            subreddit = Subreddit(
                subreddit_name="programming", display_name="Programming"
            )
            db.add(subreddit)
            db.commit()
            db.refresh(subreddit)

        # Generate unique payment intent ID for each test
        unique_id = str(uuid.uuid4())[:8]
        payment_intent_id = f"pi_test_refund_{unique_id}"

        donation = Donation(
            amount_cents=1000,
            amount_usd=10.00,
            stripe_payment_intent_id=payment_intent_id,
            status=DonationStatus.SUCCEEDED,
            customer_email="test@example.com",
            customer_name="Test User",
            is_anonymous=False,
            reddit_username="testuser",
            subreddit_id=subreddit.id,
            tier="bronze",
            commission_message="Test commission",
        )
        db.add(donation)
        db.commit()
        db.refresh(donation)
        return donation

    @patch("app.services.stripe_service.stripe")
    def test_refund_donation_success(
        self, mock_stripe, stripe_service, db: Session, sample_donation
    ):
        """Test successful refund of a donation."""
        # Mock Stripe refund response
        mock_refund = Mock()
        mock_refund.id = "re_test_refund_123"
        mock_refund.status = "succeeded"
        mock_refund.amount = 1000  # Stripe amounts are in cents
        mock_stripe.Refund.create.return_value = mock_refund

        # Perform refund
        result = stripe_service.refund_donation(db, sample_donation.id)

        # Verify Stripe API was called correctly
        mock_stripe.Refund.create.assert_called_once_with(
            payment_intent=sample_donation.stripe_payment_intent_id,
            reason="requested_by_customer",
        )

        # Verify database was updated
        db.refresh(sample_donation)
        assert sample_donation.status == DonationStatus.REFUNDED
        assert sample_donation.stripe_refund_id == "re_test_refund_123"

        # Verify return value
        assert result["success"] is True
        assert result["refund_id"] == "re_test_refund_123"
        assert result["amount_usd"] == 10.00

    @patch("app.services.stripe_service.stripe")
    def test_refund_donation_stripe_error(
        self, mock_stripe, stripe_service, db: Session, sample_donation
    ):
        """Test refund when Stripe API returns an error."""
        # Patch stripe.error.StripeError to Exception
        with patch("app.services.stripe_service.stripe.error.StripeError", Exception):
            # Mock Stripe error
            mock_stripe.Refund.create.side_effect = Exception("Stripe API error")

            # Perform refund
            result = stripe_service.refund_donation(db, sample_donation.id)

            # Verify database was not updated
            db.refresh(sample_donation)
            assert result["success"] is False
            assert "error" in result
            assert "Stripe API error" in result["error"]

    def test_refund_donation_not_found(self, stripe_service, db: Session):
        """Test refund when donation doesn't exist."""
        result = stripe_service.refund_donation(db, 99999)

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_refund_donation_already_refunded(
        self, stripe_service, db: Session, sample_donation
    ):
        """Test refund when donation is already refunded."""
        # Mark donation as already refunded
        sample_donation.status = DonationStatus.REFUNDED
        sample_donation.stripe_refund_id = "re_existing_123"
        db.commit()

        result = stripe_service.refund_donation(db, sample_donation.id)

        assert result["success"] is False
        assert "already refunded" in result["error"].lower()

    def test_refund_donation_pending_status(
        self, stripe_service, db: Session, sample_donation
    ):
        """Test refund when donation is in pending status."""
        # Mark donation as pending
        sample_donation.status = DonationStatus.PENDING
        db.commit()

        result = stripe_service.refund_donation(db, sample_donation.id)

        assert result["success"] is False
        assert "cannot refund donation with status" in result["error"].lower()

    @patch("app.services.stripe_service.stripe")
    def test_refund_donation_partial_amount(
        self, mock_stripe, stripe_service, db: Session, sample_donation
    ):
        """Test partial refund of a donation."""
        # Mock Stripe refund response
        mock_refund = Mock()
        mock_refund.id = "re_test_partial_123"
        mock_refund.status = "succeeded"
        mock_refund.amount = 500  # $5.00 in cents
        mock_stripe.Refund.create.return_value = mock_refund

        # Perform partial refund
        result = stripe_service.refund_donation(db, sample_donation.id, amount_usd=5.00)

        # Verify Stripe API was called with amount
        mock_stripe.Refund.create.assert_called_once_with(
            payment_intent=sample_donation.stripe_payment_intent_id,
            amount=500,  # $5.00 in cents
            reason="requested_by_customer",
        )

        # Verify return value
        assert result["success"] is True
        assert result["refund_id"] == "re_test_partial_123"
        assert result["amount_usd"] == 5.00

    @patch("app.services.stripe_service.stripe")
    def test_refund_donation_with_reason(
        self, mock_stripe, stripe_service, db: Session, sample_donation
    ):
        """Test refund with custom reason."""
        # Mock Stripe refund response
        mock_refund = Mock()
        mock_refund.id = "re_test_reason_123"
        mock_refund.status = "succeeded"
        mock_refund.amount = 1000
        mock_stripe.Refund.create.return_value = mock_refund

        # Perform refund with custom reason
        result = stripe_service.refund_donation(
            db, sample_donation.id, reason="duplicate"
        )

        # Verify Stripe API was called with custom reason
        mock_stripe.Refund.create.assert_called_once_with(
            payment_intent=sample_donation.stripe_payment_intent_id, reason="duplicate"
        )

        assert result["success"] is True
        assert result["refund_id"] == "re_test_reason_123"

    def test_refund_donation_invalid_amount(
        self, stripe_service, db: Session, sample_donation
    ):
        """Test refund with invalid amount."""
        result = stripe_service.refund_donation(
            db, sample_donation.id, amount_usd=15.00
        )

        assert result["success"] is False
        assert "exceeds donation amount" in result["error"].lower()

    def test_refund_donation_negative_amount(
        self, stripe_service, db: Session, sample_donation
    ):
        """Test refund with negative amount."""
        result = stripe_service.refund_donation(
            db, sample_donation.id, amount_usd=-5.00
        )

        assert result["success"] is False
        assert "invalid amount" in result["error"].lower()

    @patch("app.services.stripe_service.stripe")
    def test_refund_donation_database_error(
        self, mock_stripe, stripe_service, db: Session, sample_donation
    ):
        """Test refund when database update fails."""
        # Patch stripe.error.StripeError to Exception
        with patch("app.services.stripe_service.stripe.error.StripeError", Exception):
            # Mock Stripe refund response
            mock_refund = Mock()
            mock_refund.id = "re_test_db_error_123"
            mock_refund.status = "succeeded"
            mock_refund.amount = 1000
            mock_stripe.Refund.create.return_value = mock_refund

            # Mock database error
            with patch.object(db, "commit", side_effect=Exception("Database error")):
                result = stripe_service.refund_donation(db, sample_donation.id)

                assert result["success"] is False
                assert "database error" in result["error"].lower()

        # Verify donation status wasn't changed
        db.refresh(sample_donation)
        assert sample_donation.status == DonationStatus.SUCCEEDED
        assert sample_donation.stripe_refund_id is None
