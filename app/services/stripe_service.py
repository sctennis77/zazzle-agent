import logging
import os
from decimal import Decimal
from typing import Dict, Optional

import stripe
from sqlalchemy.orm import Session

from app.db.models import Donation
from app.models import DonationRequest, DonationStatus

logger = logging.getLogger(__name__)

# Initialize Stripe with API key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class StripeService:
    """Service for handling Stripe payment operations."""

    def __init__(self):
        """Initialize the Stripe service."""
        if not stripe.api_key:
            raise ValueError("STRIPE_SECRET_KEY environment variable is required")
        
        # Set the publishable key for client-side operations
        self.publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
        if not self.publishable_key:
            logger.warning("STRIPE_PUBLISHABLE_KEY not set - client-side operations may fail")

    def create_payment_intent(self, donation_request: DonationRequest) -> Dict:
        """
        Create a Stripe payment intent for a donation.
        
        Args:
            donation_request: The donation request containing amount and customer info
            
        Returns:
            Dict containing payment intent data
            
        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        try:
            # Convert USD amount to cents for Stripe
            amount_cents = int(donation_request.amount_usd * 100)
            
            # Prepare metadata for the payment intent
            metadata = {
                "donation_type": "one_time",
                "is_anonymous": str(donation_request.is_anonymous),
            }
            
            if donation_request.message:
                metadata["message"] = donation_request.message[:500]  # Limit message length
            
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                metadata=metadata,
                receipt_email=donation_request.customer_email,
                description=f"Donation to Zazzle Agent - ${donation_request.amount_usd}",
                automatic_payment_methods={"enabled": True},
            )
            
            logger.info(f"Created payment intent {payment_intent.id} for ${donation_request.amount_usd}")
            
            return {
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id,
                "amount_cents": amount_cents,
                "amount_usd": donation_request.amount_usd,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating payment intent: {str(e)}")
            raise

    def retrieve_payment_intent(self, payment_intent_id: str) -> Optional[Dict]:
        """
        Retrieve a payment intent from Stripe.
        
        Args:
            payment_intent_id: The Stripe payment intent ID
            
        Returns:
            Dict containing payment intent data or None if not found
            
        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                "id": payment_intent.id,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
                "status": payment_intent.status,
                "metadata": payment_intent.metadata,
                "receipt_email": getattr(payment_intent, "receipt_email", None),
                "created": payment_intent.created,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving payment intent {payment_intent_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving payment intent {payment_intent_id}: {str(e)}")
            raise

    def save_donation_to_db(self, db: Session, payment_intent_data: Dict, donation_request: DonationRequest) -> Donation:
        """
        Save donation information to the database.
        
        Args:
            db: Database session
            payment_intent_data: Data from Stripe payment intent
            donation_request: Original donation request
            
        Returns:
            Donation: The created donation record
        """
        try:
            donation = Donation(
                stripe_payment_intent_id=payment_intent_data["payment_intent_id"],
                amount_cents=payment_intent_data["amount_cents"],
                amount_usd=payment_intent_data["amount_usd"],
                currency="usd",
                status=DonationStatus.PENDING.value,
                customer_email=donation_request.customer_email,
                customer_name=donation_request.customer_name,
                message=donation_request.message,
                is_anonymous=donation_request.is_anonymous,
                stripe_metadata=payment_intent_data.get("metadata", {}),
            )
            
            db.add(donation)
            db.commit()
            db.refresh(donation)
            
            logger.info(f"Saved donation {donation.id} to database for payment intent {payment_intent_data['payment_intent_id']}")
            return donation
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving donation to database: {str(e)}")
            raise

    def update_donation_status(self, db: Session, payment_intent_id: str, status: DonationStatus) -> Optional[Donation]:
        """
        Update donation status in the database.
        
        Args:
            db: Database session
            payment_intent_id: Stripe payment intent ID
            status: New donation status
            
        Returns:
            Donation: The updated donation record or None if not found
        """
        try:
            donation = db.query(Donation).filter_by(stripe_payment_intent_id=payment_intent_id).first()
            if donation:
                donation.status = status.value
                db.commit()
                db.refresh(donation)
                logger.info(f"Updated donation {donation.id} status to {status.value}")
                return donation
            else:
                logger.warning(f"No donation found for payment intent {payment_intent_id}")
                return None
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating donation status: {str(e)}")
            raise

    def get_donation_by_payment_intent(self, db: Session, payment_intent_id: str) -> Optional[Donation]:
        """
        Get donation by Stripe payment intent ID.
        
        Args:
            db: Database session
            payment_intent_id: Stripe payment intent ID
            
        Returns:
            Donation: The donation record or None if not found
        """
        return db.query(Donation).filter_by(stripe_payment_intent_id=payment_intent_id).first()

    def get_donation_summary(self, db: Session, limit: int = 10) -> Dict:
        """
        Get donation summary statistics.
        
        Args:
            db: Database session
            limit: Number of recent donations to include
            
        Returns:
            Dict containing donation summary
        """
        try:
            # Get total successful donations
            successful_donations = db.query(Donation).filter_by(status=DonationStatus.SUCCEEDED.value).all()
            
            total_donations = len(successful_donations)
            total_amount_usd = sum(donation.amount_usd for donation in successful_donations)
            
            # Count unique donors (by email, excluding anonymous)
            unique_emails = set()
            for donation in successful_donations:
                if donation.customer_email and not donation.is_anonymous:
                    unique_emails.add(donation.customer_email)
            total_donors = len(unique_emails)
            
            # Get recent donations
            recent_donations = (
                db.query(Donation)
                .filter_by(status=DonationStatus.SUCCEEDED.value)
                .order_by(Donation.created_at.desc())
                .limit(limit)
                .all()
            )
            
            return {
                "total_donations": total_donations,
                "total_amount_usd": total_amount_usd,
                "total_donors": total_donors,
                "recent_donations": recent_donations,
            }
            
        except Exception as e:
            logger.error(f"Error getting donation summary: {str(e)}")
            raise 