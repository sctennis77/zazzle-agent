import logging
import os
from decimal import Decimal
from typing import Dict, Optional

import stripe
from sqlalchemy.orm import Session

from app.db.models import Donation, Sponsor, SponsorTier, SubredditFundraisingGoal, PipelineTask
from app.models import DonationRequest, DonationStatus
from app.subreddit_tier_service import SubredditTierService

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
            amount_cents = int(float(donation_request.amount_usd) * 100)
            
            # Prepare metadata for the payment intent
            metadata = {
                "donation_type": donation_request.donation_type,
                "is_anonymous": str(donation_request.is_anonymous),
            }
            
            if donation_request.message:
                metadata["message"] = donation_request.message[:500]  # Limit message length
            
            if donation_request.subreddit:
                metadata["subreddit"] = donation_request.subreddit[:100]  # Limit subreddit length
            
            if donation_request.reddit_username:
                metadata["reddit_username"] = donation_request.reddit_username[:100]  # Limit username length
            
            if donation_request.post_id:
                metadata["post_id"] = donation_request.post_id[:32]  # Limit post ID length
            
            if donation_request.commission_message:
                metadata["commission_message"] = donation_request.commission_message[:500]  # Limit message length
            
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

    def update_payment_intent(self, payment_intent_id: str, donation_request: DonationRequest) -> Dict:
        """
        Update a Stripe payment intent with new metadata and amount.
        
        Args:
            payment_intent_id: The Stripe payment intent ID to update
            donation_request: The donation request containing updated info
            
        Returns:
            Dict containing updated payment intent data
            
        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        try:
            # First, retrieve the payment intent to check if it exists and can be updated
            try:
                existing_payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                logger.info(f"Found existing payment intent {payment_intent_id} with status: {existing_payment_intent.status}")
            except stripe.error.InvalidRequestError as e:
                logger.error(f"Payment intent {payment_intent_id} not found: {str(e)}")
                raise Exception(f"Payment intent {payment_intent_id} not found")
            
            # Check if payment intent can be modified
            if existing_payment_intent.status in ['succeeded', 'canceled', 'processing']:
                logger.warning(f"Payment intent {payment_intent_id} cannot be modified in status: {existing_payment_intent.status}")
                # Return the existing payment intent data instead of trying to modify
                return {
                    "client_secret": existing_payment_intent.client_secret,
                    "payment_intent_id": existing_payment_intent.id,
                    "amount_cents": existing_payment_intent.amount,
                    "amount_usd": str(existing_payment_intent.amount / 100),
                }
            
            # Convert USD amount to cents for Stripe
            amount_cents = int(float(donation_request.amount_usd) * 100)
            
            # Prepare metadata for the payment intent
            metadata = {
                "donation_type": donation_request.donation_type,
                "is_anonymous": str(donation_request.is_anonymous),
            }
            
            if donation_request.message:
                metadata["message"] = donation_request.message[:500]  # Limit message length
            
            if donation_request.subreddit:
                metadata["subreddit"] = donation_request.subreddit[:100]  # Limit subreddit length
            
            if donation_request.reddit_username:
                metadata["reddit_username"] = donation_request.reddit_username[:100]  # Limit username length
            
            if donation_request.post_id:
                metadata["post_id"] = donation_request.post_id[:32]  # Limit post ID length
            
            if donation_request.commission_message:
                metadata["commission_message"] = donation_request.commission_message[:500]  # Limit message length
            
            # Update payment intent
            payment_intent = stripe.PaymentIntent.modify(
                payment_intent_id,
                amount=amount_cents,
                metadata=metadata,
                receipt_email=donation_request.customer_email,
                description=f"Donation to Zazzle Agent - ${donation_request.amount_usd}",
            )
            
            logger.info(f"Updated payment intent {payment_intent.id} for ${donation_request.amount_usd}")
            
            return {
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id,
                "amount_cents": amount_cents,
                "amount_usd": donation_request.amount_usd,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error updating payment intent {payment_intent_id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating payment intent {payment_intent_id}: {str(e)}")
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
            # Check if donation already exists for this payment intent
            existing_donation = db.query(Donation).filter_by(
                stripe_payment_intent_id=payment_intent_data["payment_intent_id"]
            ).first()
            
            if existing_donation:
                logger.info(f"Donation already exists for payment intent {payment_intent_data['payment_intent_id']} (ID: {existing_donation.id})")
                return existing_donation
            
            # Get or create subreddit entity
            subreddit_id = None
            if donation_request.subreddit:
                from app.subreddit_service import get_subreddit_service
                subreddit_service = get_subreddit_service()
                subreddit = subreddit_service.get_or_create_subreddit(donation_request.subreddit, db)
                subreddit_id = subreddit.id

            # Find active fundraising goal for the subreddit, if any
            fundraising_goal_id = None
            if subreddit_id:
                goal = db.query(SubredditFundraisingGoal).filter_by(
                    subreddit_id=subreddit_id,
                    status="active"
                ).order_by(SubredditFundraisingGoal.created_at.desc()).first()
                if goal:
                    fundraising_goal_id = goal.id

            donation = Donation(
                stripe_payment_intent_id=payment_intent_data["payment_intent_id"],
                amount_cents=payment_intent_data["amount_cents"],
                amount_usd=payment_intent_data["amount_usd"],
                currency="usd",
                status=DonationStatus.PENDING.value,
                customer_email=donation_request.customer_email,
                customer_name=donation_request.customer_name,
                message=donation_request.message,
                subreddit_id=subreddit_id,
                reddit_username=donation_request.reddit_username,
                is_anonymous=donation_request.is_anonymous,
                stripe_metadata=payment_intent_data.get("metadata", {}),
                subreddit_fundraising_goal_id=fundraising_goal_id,
                donation_type=donation_request.donation_type,
                post_id=donation_request.post_id,
                commission_message=donation_request.commission_message,
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

    def create_sponsor_record(self, db: Session, donation: Donation) -> Optional[Sponsor]:
        """
        Create a sponsor record when a donation succeeds.
        
        Args:
            db: Database session
            donation: The successful donation record
            
        Returns:
            Sponsor: The created sponsor record or None if no matching tier
        """
        try:
            # Find the appropriate sponsor tier based on donation amount
            tier = (
                db.query(SponsorTier)
                .filter(SponsorTier.min_amount <= donation.amount_usd)
                .order_by(SponsorTier.min_amount.desc())
                .first()
            )
            
            if not tier:
                logger.warning(f"No sponsor tier found for donation amount ${donation.amount_usd}")
                return None
            
            # Check if sponsor record already exists
            existing_sponsor = db.query(Sponsor).filter_by(donation_id=donation.id).first()
            if existing_sponsor:
                logger.info(f"Sponsor record already exists for donation {donation.id}")
                return existing_sponsor
            
            # Create sponsor record
            sponsor = Sponsor(
                donation_id=donation.id,
                tier_id=tier.id,
                subreddit_id=donation.subreddit_id,
                status="active"
            )
            
            db.add(sponsor)
            db.commit()
            db.refresh(sponsor)
            
            logger.info(f"Created sponsor record {sponsor.id} for donation {donation.id} with tier {tier.name}")
            return sponsor
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating sponsor record: {str(e)}")
            raise

    def process_subreddit_tiers(self, db: Session, donation: Donation) -> Dict:
        """
        Process subreddit tiers and fundraising goals for a donation.
        
        Args:
            db: Database session
            donation: The successful donation record
            
        Returns:
            Dict: Processing results
        """
        try:
            if not donation.subreddit_id:
                return {"subreddit": None, "completed_tiers": [], "completed_goals": []}
            
            # Get subreddit name for logging
            subreddit_name = donation.subreddit.subreddit_name if donation.subreddit else "unknown"
            
            tier_service = SubredditTierService(db)
            results = tier_service.process_donation(donation)
            
            logger.info(f"Processed subreddit tiers for {subreddit_name}: "
                      f"{len(results['completed_tiers'])} tiers, {len(results['completed_goals'])} goals")
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing subreddit tiers: {str(e)}")
            subreddit_name = donation.subreddit.subreddit_name if donation.subreddit else "unknown"
            return {"subreddit": subreddit_name, "completed_tiers": [], "completed_goals": [], "error": str(e)}

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
                
                # Create sponsor record if donation succeeded
                if status == DonationStatus.SUCCEEDED:
                    sponsor = self.create_sponsor_record(db, donation)
                    
                    # Create pipeline task for the sponsor
                    if sponsor:
                        self.create_sponsor_task(db, sponsor, donation)
                    
                    # Process subreddit tiers and fundraising goals
                    tier_results = self.process_subreddit_tiers(db, donation)
                    logger.info(f"Subreddit tier processing results: {tier_results}")
                
                return donation
            else:
                logger.warning(f"No donation found for payment intent {payment_intent_id}")
                return None
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating donation status: {str(e)}")
            raise

    def create_sponsor_task(self, db: Session, sponsor: Sponsor, donation: Donation) -> Optional[PipelineTask]:
        """
        Create a pipeline task for a sponsor when their donation succeeds.
        Only creates tasks for commission donations.
        
        Args:
            db: Database session
            sponsor: The sponsor record
            donation: The donation record
            
        Returns:
            PipelineTask: The created task or None if creation failed or not a commission
        """
        try:
            # Only create pipeline tasks for commission donations
            if donation.donation_type != "commission":
                logger.info(f"Skipping task creation for {donation.donation_type} donation {donation.id}")
                return None
            
            from app.task_queue import TaskQueue
            
            task_queue = TaskQueue(db)
            
            # Determine subreddit for the task
            subreddit_id = donation.subreddit_id
            if not subreddit_id:
                logger.error(f"No subreddit_id found for commission donation {donation.id}")
                return None
            
            # Determine task type and context based on donation type and tier
            task_type = "SUBREDDIT_POST"
            context_data = {
                "donation_id": donation.id,
                "donation_amount": float(donation.amount_usd),
                "sponsor_tier": sponsor.tier.name if sponsor.tier else "unknown",
                "customer_name": donation.customer_name,
                "is_anonymous": donation.is_anonymous,
                "donation_type": donation.donation_type,
                "commission_message": donation.commission_message,
            }
            
            # Handle commissioning logic
            tier_name = sponsor.tier.name.lower() if sponsor.tier else ""
            
            if donation.post_id:
                # Specific post commission (any tier can specify a post)
                task_type = "SPECIFIC_POST"
                context_data.update({
                    "commission_type": "specific_post",
                    "post_id": donation.post_id,
                })
                logger.info(f"Creating specific post commission task for {tier_name} tier - post {donation.post_id}")
            else:
                # Random post commission (default behavior)
                task_type = "SUBREDDIT_POST"
                context_data.update({
                    "commission_type": "random_post",
                })
                logger.info(f"Creating random post commission task for {tier_name} tier")
            
            # Create task with sponsor priority (higher priority for sponsors)
            task = task_queue.add_task(
                task_type=task_type,
                subreddit_id=subreddit_id,
                sponsor_id=sponsor.id,
                priority=10,  # Higher priority for sponsor tasks
                context_data=context_data
            )
            
            subreddit_name = donation.subreddit.subreddit_name if donation.subreddit else "unknown"
            logger.info(f"Created commission task {task.id} for sponsor {sponsor.id} "
                      f"in r/{subreddit_name} with priority {task.priority}")
            return task
            
        except Exception as e:
            logger.error(f"Error creating sponsor task: {str(e)}")
            return None

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