import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Donation, Subreddit
from app.models import DonationStatus


class TestRefundMigration:
    """Test cases for the refund migration functionality."""

    def test_stripe_refund_id_column_exists(self, db: Session):
        """Test that the stripe_refund_id column exists in the donations table."""
        # Check if the column exists by querying the table schema
        result = db.execute(
            text(
                """
            SELECT name 
            FROM pragma_table_info('donations') 
            WHERE name = 'stripe_refund_id'
        """
            )
        )

        column_exists = result.fetchone() is not None
        assert column_exists, "stripe_refund_id column should exist in donations table"

    def test_stripe_refund_id_column_type(self, db: Session):
        """Test that the stripe_refund_id column has the correct type."""
        result = db.execute(
            text(
                """
            SELECT type 
            FROM pragma_table_info('donations') 
            WHERE name = 'stripe_refund_id'
        """
            )
        )

        column_info = result.fetchone()
        assert column_info is not None, "stripe_refund_id column should exist"
        assert (
            column_info[0] == "VARCHAR(255)"
        ), "stripe_refund_id should be VARCHAR(255) type"

    def test_stripe_refund_id_nullable(self, db: Session):
        """Test that the stripe_refund_id column allows NULL values."""
        result = db.execute(
            text(
                """
            SELECT "notnull" 
            FROM pragma_table_info('donations') 
            WHERE name = 'stripe_refund_id'
        """
            )
        )

        column_info = result.fetchone()
        assert column_info is not None, "stripe_refund_id column should exist"
        assert column_info[0] == 0, "stripe_refund_id should allow NULL values"

    def test_can_create_donation_without_refund_id(self, db: Session):
        """Test that donations can be created without a refund ID."""
        # Get or create subreddit
        subreddit = db.query(Subreddit).filter_by(subreddit_name="programming").first()
        if not subreddit:
            subreddit = Subreddit(
                subreddit_name="programming", display_name="Programming"
            )
            db.add(subreddit)
            db.commit()
            db.refresh(subreddit)

        donation = Donation(
            amount_usd=10.00,
            amount_cents=int(10.00 * 100),
            stripe_payment_intent_id="pi_test_migration_123",
            status=DonationStatus.SUCCEEDED,
            customer_email="test@example.com",
            customer_name="Test User",
            is_anonymous=False,
            reddit_username="testuser",
            subreddit_id=subreddit.id,
            tier="bronze",
        )

        db.add(donation)
        db.commit()
        db.refresh(donation)

        assert donation.stripe_refund_id is None
        assert donation.stripe_payment_intent_id == "pi_test_migration_123"

    def test_can_create_donation_with_refund_id(self, db: Session):
        """Test that donations can be created with a refund ID."""
        # Get or create subreddit
        subreddit = db.query(Subreddit).filter_by(subreddit_name="programming").first()
        if not subreddit:
            subreddit = Subreddit(
                subreddit_name="programming", display_name="Programming"
            )
            db.add(subreddit)
            db.commit()
            db.refresh(subreddit)

        donation = Donation(
            amount_usd=15.00,
            amount_cents=int(15.00 * 100),
            stripe_payment_intent_id="pi_test_migration_456",
            stripe_refund_id="re_test_migration_456",
            status=DonationStatus.REFUNDED,
            customer_email="test@example.com",
            customer_name="Test User",
            is_anonymous=False,
            reddit_username="testuser",
            subreddit_id=subreddit.id,
            tier="silver",
        )

        db.add(donation)
        db.commit()
        db.refresh(donation)

        assert donation.stripe_refund_id == "re_test_migration_456"
        assert donation.status == DonationStatus.REFUNDED

    def test_can_update_donation_refund_id(self, db: Session):
        """Test that donation refund ID can be updated."""
        # Create donation without refund ID
        # Get or create subreddit
        subreddit = db.query(Subreddit).filter_by(subreddit_name="programming").first()
        if not subreddit:
            subreddit = Subreddit(
                subreddit_name="programming", display_name="Programming"
            )
            db.add(subreddit)
            db.commit()
            db.refresh(subreddit)

        donation = Donation(
            amount_usd=20.00,
            amount_cents=int(20.00 * 100),
            stripe_payment_intent_id="pi_test_migration_789",
            status=DonationStatus.SUCCEEDED,
            customer_email="test@example.com",
            customer_name="Test User",
            is_anonymous=False,
            reddit_username="testuser",
            subreddit_id=subreddit.id,
            tier="gold",
        )

        db.add(donation)
        db.commit()
        db.refresh(donation)

        # Initially no refund ID
        assert donation.stripe_refund_id is None

        # Update with refund ID
        donation.stripe_refund_id = "re_test_migration_789"
        donation.status = DonationStatus.REFUNDED
        db.commit()
        db.refresh(donation)

        # Verify update
        assert donation.stripe_refund_id == "re_test_migration_789"
        assert donation.status == DonationStatus.REFUNDED

    def test_refund_id_length_limits(self, db: Session):
        """Test that refund ID can handle typical Stripe refund ID lengths."""
        # Stripe refund IDs are typically 27 characters
        long_refund_id = "re_test_migration_very_long_id_123"

        # Get or create subreddit
        subreddit = db.query(Subreddit).filter_by(subreddit_name="programming").first()
        if not subreddit:
            subreddit = Subreddit(
                subreddit_name="programming", display_name="Programming"
            )
            db.add(subreddit)
            db.commit()
            db.refresh(subreddit)

        donation = Donation(
            amount_usd=5.00,
            amount_cents=int(5.00 * 100),
            stripe_payment_intent_id="pi_test_migration_long",
            stripe_refund_id=long_refund_id,
            status=DonationStatus.REFUNDED,
            customer_email="test@example.com",
            customer_name="Test User",
            is_anonymous=False,
            reddit_username="testuser",
            subreddit_id=subreddit.id,
            tier="bronze",
        )

        db.add(donation)
        db.commit()
        db.refresh(donation)

        assert donation.stripe_refund_id == long_refund_id

    def test_query_donations_by_refund_status(self, db: Session):
        """Test that we can query donations by refund status."""
        # Get or create subreddit
        subreddit = db.query(Subreddit).filter_by(subreddit_name="programming").first()
        if not subreddit:
            subreddit = Subreddit(
                subreddit_name="programming", display_name="Programming"
            )
            db.add(subreddit)
            db.commit()
            db.refresh(subreddit)

        # Create refunded donation
        refunded_donation = Donation(
            amount_usd=10.00,
            amount_cents=int(10.00 * 100),
            stripe_payment_intent_id="pi_test_query_123",
            stripe_refund_id="re_test_query_123",
            status=DonationStatus.REFUNDED,
            customer_email="test@example.com",
            customer_name="Test User",
            is_anonymous=False,
            reddit_username="testuser",
            subreddit_id=subreddit.id,
            tier="bronze",
        )

        # Create non-refunded donation
        non_refunded_donation = Donation(
            amount_usd=15.00,
            amount_cents=int(15.00 * 100),
            stripe_payment_intent_id="pi_test_query_456",
            status=DonationStatus.SUCCEEDED,
            customer_email="test@example.com",
            customer_name="Test User",
            is_anonymous=False,
            reddit_username="testuser",
            subreddit_id=subreddit.id,
            tier="silver",
        )

        db.add_all([refunded_donation, non_refunded_donation])
        db.commit()

        # Query refunded donations
        refunded_donations = (
            db.query(Donation).filter(Donation.stripe_refund_id.isnot(None)).all()
        )

        assert len(refunded_donations) >= 1
        assert any(
            d.stripe_refund_id == "re_test_query_123" for d in refunded_donations
        )

        # Query non-refunded donations
        non_refunded_donations = (
            db.query(Donation).filter(Donation.stripe_refund_id.is_(None)).all()
        )

        assert len(non_refunded_donations) >= 1
        assert any(
            d.stripe_payment_intent_id == "pi_test_query_456"
            for d in non_refunded_donations
        )

    def test_refund_id_uniqueness_not_enforced(self, db: Session):
        """Test that refund IDs are not required to be unique (same refund can apply to multiple charges)."""
        # Get or create subreddit
        subreddit = db.query(Subreddit).filter_by(subreddit_name="programming").first()
        if not subreddit:
            subreddit = Subreddit(
                subreddit_name="programming", display_name="Programming"
            )
            db.add(subreddit)
            db.commit()
            db.refresh(subreddit)

        # Create two donations with the same refund ID
        donation1 = Donation(
            amount_usd=10.00,
            amount_cents=int(10.00 * 100),
            stripe_payment_intent_id="pi_test_duplicate_1",
            stripe_refund_id="re_test_duplicate_123",
            status=DonationStatus.REFUNDED,
            customer_email="test@example.com",
            customer_name="Test User",
            is_anonymous=False,
            reddit_username="testuser",
            subreddit_id=subreddit.id,
            tier="bronze",
        )

        donation2 = Donation(
            amount_usd=15.00,
            amount_cents=int(15.00 * 100),
            stripe_payment_intent_id="pi_test_duplicate_2",
            stripe_refund_id="re_test_duplicate_123",  # Same refund ID
            status=DonationStatus.REFUNDED,
            customer_email="test@example.com",
            customer_name="Test User",
            is_anonymous=False,
            reddit_username="testuser",
            subreddit_id=subreddit.id,
            tier="silver",
        )

        db.add_all([donation1, donation2])
        db.commit()

        # Both should be saved successfully
        assert donation1.stripe_refund_id == "re_test_duplicate_123"
        assert donation2.stripe_refund_id == "re_test_duplicate_123"

    def test_migration_backward_compatibility(self, db: Session):
        """Test that existing donations without refund IDs still work."""
        # This test ensures that the migration doesn't break existing data
        # Create a donation as if it existed before the migration
        # Get or create subreddit
        subreddit = db.query(Subreddit).filter_by(subreddit_name="programming").first()
        if not subreddit:
            subreddit = Subreddit(
                subreddit_name="programming", display_name="Programming"
            )
            db.add(subreddit)
            db.commit()
            db.refresh(subreddit)

        donation = Donation(
            amount_usd=25.00,
            amount_cents=int(25.00 * 100),
            stripe_payment_intent_id="pi_test_backward_123",
            status=DonationStatus.SUCCEEDED,
            customer_email="test@example.com",
            customer_name="Test User",
            is_anonymous=False,
            reddit_username="testuser",
            subreddit_id=subreddit.id,
            tier="gold",
        )

        db.add(donation)
        db.commit()
        db.refresh(donation)

        # Should work without refund ID
        assert donation.stripe_refund_id is None
        assert donation.amount_usd == 25.00
        assert donation.status == DonationStatus.SUCCEEDED
