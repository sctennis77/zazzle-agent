import logging
import os
import threading
import time
from decimal import Decimal
from typing import Dict, Optional

import stripe
from sqlalchemy.orm import Session

from app.db.models import Donation, PipelineTask, SubredditFundraisingGoal
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
            logger.warning(
                "STRIPE_PUBLISHABLE_KEY not set - client-side operations may fail"
            )

        # In-memory lock for payment intent operations
        self._payment_intent_locks = {}
        self._lock_mutex = threading.Lock()

    def _acquire_payment_intent_lock(
        self, payment_intent_id: str, timeout: int = 30
    ) -> bool:
        """
        Acquire a lock for a payment intent to prevent concurrent modifications.

        Args:
            payment_intent_id: The payment intent ID to lock
            timeout: Maximum time to wait for the lock in seconds

        Returns:
            bool: True if lock was acquired, False otherwise
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            with self._lock_mutex:
                if payment_intent_id not in self._payment_intent_locks:
                    self._payment_intent_locks[payment_intent_id] = threading.Lock()

                if self._payment_intent_locks[payment_intent_id].acquire(
                    blocking=False
                ):
                    logger.debug(
                        f"Acquired lock for payment intent {payment_intent_id}"
                    )
                    return True

            # Wait a bit before trying again
            time.sleep(0.1)

        logger.warning(
            f"Failed to acquire lock for payment intent {payment_intent_id} after {timeout}s"
        )
        return False

    def _release_payment_intent_lock(self, payment_intent_id: str):
        """
        Release a lock for a payment intent.

        Args:
            payment_intent_id: The payment intent ID to unlock
        """
        with self._lock_mutex:
            if payment_intent_id in self._payment_intent_locks:
                self._payment_intent_locks[payment_intent_id].release()
                logger.debug(f"Released lock for payment intent {payment_intent_id}")

    def _validate_and_prepare_metadata(self, donation_request: DonationRequest) -> Dict:
        """
        Validate and prepare metadata for Stripe payment intent.

        Stripe limits:
        - 500 characters per metadata key
        - 1KB total metadata size
        - 50 keys maximum

        Args:
            donation_request: The donation request containing metadata

        Returns:
            Dict: Validated and sanitized metadata

        Raises:
            ValueError: If metadata validation fails
        """
        metadata = {}
        total_size = 0

        # Core required fields
        metadata["donation_type"] = str(donation_request.donation_type)[:50]
        metadata["is_anonymous"] = str(donation_request.is_anonymous)

        # Optional fields with validation
        if donation_request.message:
            sanitized_message = str(donation_request.message)[:500]
            metadata["message"] = sanitized_message

        if donation_request.subreddit:
            sanitized_subreddit = str(donation_request.subreddit)[:100]
            metadata["subreddit"] = sanitized_subreddit

        if donation_request.reddit_username:
            sanitized_username = str(donation_request.reddit_username)[:100]
            metadata["reddit_username"] = sanitized_username

        if donation_request.post_id:
            sanitized_post_id = str(donation_request.post_id)[:32]
            metadata["post_id"] = sanitized_post_id

        if donation_request.commission_message:
            sanitized_commission_message = str(donation_request.commission_message)[
                :500
            ]
            metadata["commission_message"] = sanitized_commission_message

        if donation_request.commission_type:
            sanitized_commission_type = str(donation_request.commission_type)[:50]
            metadata["commission_type"] = sanitized_commission_type

        # Validate total metadata size (1KB limit)
        for key, value in metadata.items():
            total_size += len(key) + len(str(value))

        if total_size > 1024:  # 1KB limit
            logger.warning(f"Metadata size {total_size} exceeds 1KB limit, truncating")
            # Remove less important fields first
            if "message" in metadata:
                del metadata["message"]
                total_size = sum(len(k) + len(str(v)) for k, v in metadata.items())
            if total_size > 1024 and "commission_message" in metadata:
                del metadata["commission_message"]
                total_size = sum(len(k) + len(str(v)) for k, v in metadata.items())
            if total_size > 1024:
                raise ValueError(
                    f"Metadata size {total_size} still exceeds 1KB limit after truncation"
                )

        logger.debug(f"Prepared metadata with {len(metadata)} keys, {total_size} bytes")
        return metadata

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

            # Validate and prepare metadata
            metadata = self._validate_and_prepare_metadata(donation_request)

            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="usd",
                metadata=metadata,
                receipt_email=donation_request.customer_email,
                description=f"Donation to Zazzle Agent - ${donation_request.amount_usd}",
                automatic_payment_methods={"enabled": True},
            )

            logger.info(
                f"Created payment intent {payment_intent.id} for ${donation_request.amount_usd}"
            )

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
            logger.error(
                f"Stripe error retrieving payment intent {payment_intent_id}: {str(e)}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving payment intent {payment_intent_id}: {str(e)}"
            )
            raise

    def update_payment_intent(
        self, payment_intent_id: str, donation_request: DonationRequest
    ) -> Dict:
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
        # Acquire lock to prevent concurrent modifications
        if not self._acquire_payment_intent_lock(payment_intent_id):
            raise Exception(
                f"Unable to acquire lock for payment intent {payment_intent_id}"
            )

        try:
            # First, retrieve the payment intent to check if it exists and can be updated
            try:
                existing_payment_intent = stripe.PaymentIntent.retrieve(
                    payment_intent_id
                )
                logger.info(
                    f"Found existing payment intent {payment_intent_id} with status: {existing_payment_intent.status}"
                )
            except stripe.error.InvalidRequestError as e:
                logger.error(f"Payment intent {payment_intent_id} not found: {str(e)}")
                raise Exception(f"Payment intent {payment_intent_id} not found")

            # Check if payment intent can be modified
            if existing_payment_intent.status in [
                "succeeded",
                "canceled",
                "processing",
            ]:
                logger.warning(
                    f"Payment intent {payment_intent_id} cannot be modified in status: {existing_payment_intent.status}"
                )
                # Return the existing payment intent data instead of trying to modify
                return {
                    "client_secret": existing_payment_intent.client_secret,
                    "payment_intent_id": existing_payment_intent.id,
                    "amount_cents": existing_payment_intent.amount,
                    "amount_usd": str(existing_payment_intent.amount / 100),
                }

            # Convert USD amount to cents for Stripe
            amount_cents = int(float(donation_request.amount_usd) * 100)

            # Validate and prepare metadata
            metadata = self._validate_and_prepare_metadata(donation_request)

            # Update payment intent
            payment_intent = stripe.PaymentIntent.modify(
                payment_intent_id,
                amount=amount_cents,
                metadata=metadata,
                receipt_email=donation_request.customer_email,
                description=f"Donation to Zazzle Agent - ${donation_request.amount_usd}",
            )

            logger.info(
                f"Updated payment intent {payment_intent.id} for ${donation_request.amount_usd}"
            )

            return {
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id,
                "amount_cents": amount_cents,
                "amount_usd": donation_request.amount_usd,
            }

        except stripe.error.StripeError as e:
            logger.error(
                f"Stripe error updating payment intent {payment_intent_id}: {str(e)}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error updating payment intent {payment_intent_id}: {str(e)}"
            )
            raise
        finally:
            # Always release the lock
            self._release_payment_intent_lock(payment_intent_id)

    def save_donation_to_db(
        self, db: Session, payment_intent_data: Dict, donation_request: DonationRequest
    ) -> Donation:
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
            existing_donation = (
                db.query(Donation)
                .filter_by(
                    stripe_payment_intent_id=payment_intent_data["payment_intent_id"]
                )
                .first()
            )

            if existing_donation:
                logger.info(
                    f"Donation already exists for payment intent {payment_intent_data['payment_intent_id']} (ID: {existing_donation.id})"
                )
                return existing_donation

            # Get or create subreddit entity
            subreddit_id = None
            if donation_request.subreddit:
                from app.subreddit_service import get_subreddit_service

                subreddit_service = get_subreddit_service()
                subreddit = subreddit_service.get_or_create_subreddit(
                    donation_request.subreddit, db
                )
                subreddit_id = subreddit.id

            # Find active fundraising goal for the subreddit, if any
            fundraising_goal_id = None
            if subreddit_id:
                goal = (
                    db.query(SubredditFundraisingGoal)
                    .filter_by(subreddit_id=subreddit_id, status="active")
                    .order_by(SubredditFundraisingGoal.created_at.desc())
                    .first()
                )
                if goal:
                    fundraising_goal_id = goal.id

            # Import tier function and SourceType
            from app.db.models import SourceType
            from app.models import get_tier_from_amount

            # Determine tier based on amount
            tier = get_tier_from_amount(donation_request.amount_usd)

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
                subreddit_fundraising_goal_id=fundraising_goal_id,
                donation_type=donation_request.donation_type,
                commission_type=donation_request.commission_type,
                post_id=donation_request.post_id,
                commission_message=donation_request.commission_message,
                source=SourceType.STRIPE,
            )

            db.add(donation)
            db.commit()
            db.refresh(donation)

            logger.info(
                f"Saved donation {donation.id} to database for payment intent {payment_intent_data['payment_intent_id']}"
            )
            return donation

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving donation to database: {str(e)}")
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
            subreddit_name = (
                donation.subreddit.subreddit_name if donation.subreddit else "unknown"
            )

            tier_service = SubredditTierService(db)
            results = tier_service.process_donation(donation)

            logger.info(
                f"Processed subreddit tiers for {subreddit_name}: "
                f"{len(results['completed_tiers'])} tiers, {len(results['completed_goals'])} goals"
            )

            return results

        except Exception as e:
            logger.error(f"Error processing subreddit tiers: {str(e)}")
            subreddit_name = (
                donation.subreddit.subreddit_name if donation.subreddit else "unknown"
            )
            return {
                "subreddit": subreddit_name,
                "completed_tiers": [],
                "completed_goals": [],
                "error": str(e),
            }

    def update_donation_status(
        self, db: Session, payment_intent_id: str, status: DonationStatus
    ) -> Optional[Donation]:
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
            donation = (
                db.query(Donation)
                .filter_by(stripe_payment_intent_id=payment_intent_id)
                .first()
            )
            if donation:
                donation.status = status.value
                db.commit()
                db.refresh(donation)
                logger.info(f"Updated donation {donation.id} status to {status.value}")

                # Create pipeline task if donation succeeded and is a commission
                if (
                    status == DonationStatus.SUCCEEDED
                    and donation.donation_type == "commission"
                ):
                    self.create_commission_task(db, donation)

                # Process subreddit tiers and fundraising goals
                tier_results = self.process_subreddit_tiers(db, donation)
                logger.info(f"Subreddit tier processing results: {tier_results}")

                return donation
            else:
                logger.warning(
                    f"No donation found for payment intent {payment_intent_id}"
                )
                return None

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating donation status: {str(e)}")
            raise

    def create_commission_task(
        self, db: Session, donation: Donation
    ) -> Optional[PipelineTask]:
        """
        Create a pipeline task for a commission donation when it succeeds.

        Args:
            db: Database session
            donation: The commission donation record

        Returns:
            PipelineTask: The created task or None if creation failed
        """
        try:
            # Only create pipeline tasks for commission donations
            if donation.donation_type != "commission":
                logger.info(
                    f"Skipping task creation for {donation.donation_type} donation {donation.id}"
                )
                return None

            # Check if a task already exists for this donation to prevent duplicates
            existing_task = (
                db.query(PipelineTask)
                .filter_by(donation_id=donation.id, status="pending")
                .first()
            )

            if existing_task:
                logger.info(
                    f"Task already exists for donation {donation.id} (task {existing_task.id}), skipping duplicate creation"
                )
                return existing_task

            from app.task_queue import TaskQueue

            task_queue = TaskQueue(db)

            # Determine task type and context based on commission type
            task_type = "SUBREDDIT_POST"
            context_data = {
                "donation_id": donation.id,
                "donation_amount": float(donation.amount_usd),
                "tier": donation.tier,
                "customer_name": donation.customer_name,
                "reddit_username": donation.reddit_username,
                "is_anonymous": donation.is_anonymous,
                "donation_type": donation.donation_type,
                "commission_type": donation.commission_type,
                "commission_message": donation.commission_message,
            }

            # Handle commissioning logic based on commission type
            if donation.commission_type == "specific_post" and donation.post_id:
                # Specific post commission - still use SUBREDDIT_POST type but include post_id in context
                task_type = "SUBREDDIT_POST"
                context_data.update(
                    {
                        "post_id": donation.post_id,
                        "commission_type": "specific_post",
                    }
                )
                logger.info(
                    f"Creating specific post commission task for {donation.tier} tier - post {donation.post_id}"
                )
            elif donation.commission_type == "random_subreddit":
                # Random post from selected subreddit
                task_type = "SUBREDDIT_POST"
                context_data.update(
                    {
                        "commission_type": "random_subreddit",
                    }
                )
                logger.info(
                    f"Creating random subreddit commission task for {donation.tier} tier"
                )
            elif donation.commission_type == "random_random":
                # Random post from random subreddit - select a random subreddit
                from app.agents.reddit_agent import pick_subreddit

                random_subreddit_name = pick_subreddit(db)

                # Get or create the random subreddit entity
                from app.subreddit_service import get_subreddit_service

                subreddit_service = get_subreddit_service()
                random_subreddit = subreddit_service.get_or_create_subreddit(
                    random_subreddit_name, db
                )

                # Update the donation's subreddit_id to the randomly selected subreddit
                donation.subreddit_id = random_subreddit.id
                db.commit()

                # Use the randomly selected subreddit for the task
                subreddit_id = random_subreddit.id

                task_type = "SUBREDDIT_POST"
                context_data.update(
                    {
                        "commission_type": "random_random",
                        "selected_subreddit": random_subreddit_name,
                    }
                )
                logger.info(
                    f"Creating random_random commission task for {donation.tier} tier - selected subreddit: {random_subreddit_name}"
                )
            else:
                # Default to random subreddit
                task_type = "SUBREDDIT_POST"
                context_data.update(
                    {
                        "commission_type": "random_subreddit",
                    }
                )
                logger.info(
                    f"Creating default commission task for {donation.tier} tier"
                )

            # Determine subreddit for the task (after random selection for random_random)
            subreddit_id = donation.subreddit_id
            if not subreddit_id:
                logger.error(
                    f"No subreddit_id found for commission donation {donation.id}"
                )
                return None

            # Create task with commission priority
            task = task_queue.add_task(
                task_type=task_type,
                subreddit_id=subreddit_id,
                donation_id=donation.id,
                priority=10,  # Higher priority for commission tasks
                context_data=context_data,
            )

            subreddit_name = (
                donation.subreddit.subreddit_name if donation.subreddit else "unknown"
            )
            logger.info(
                f"Created commission task {task.id} for donation {donation.id} "
                f"in r/{subreddit_name} with priority {task.priority}"
            )
            return task

        except Exception as e:
            logger.error(f"Error creating commission task: {str(e)}")
            return None

    def get_donation_by_payment_intent(
        self, db: Session, payment_intent_id: str
    ) -> Optional[Donation]:
        """
        Get donation by Stripe payment intent ID.

        Args:
            db: Database session
            payment_intent_id: Stripe payment intent ID

        Returns:
            Donation: The donation record or None if not found
        """
        return (
            db.query(Donation)
            .filter_by(stripe_payment_intent_id=payment_intent_id)
            .first()
        )

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
            successful_donations = (
                db.query(Donation)
                .filter_by(status=DonationStatus.SUCCEEDED.value)
                .all()
            )

            total_donations = len(successful_donations)
            total_amount_usd = sum(
                donation.amount_usd for donation in successful_donations
            )

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

    def refund_payment_intent(
        self,
        db: Session,
        payment_intent_id: str,
        reason: str = "Commission processing failed",
    ) -> Optional[Dict]:
        """
        Refund a payment intent and update the donation status.

        Args:
            db: Database session
            payment_intent_id: Stripe payment intent ID to refund
            reason: Reason for the refund (for Stripe metadata)

        Returns:
            Dict containing refund information or None if refund failed
        """
        try:
            # First, get the donation to verify it exists and can be refunded
            donation = (
                db.query(Donation)
                .filter_by(stripe_payment_intent_id=payment_intent_id)
                .first()
            )
            if not donation:
                logger.error(
                    f"No donation found for payment intent {payment_intent_id}"
                )
                return None

            # Check if donation is already refunded
            if donation.status == "refunded":
                logger.info(
                    f"Donation {donation.id} already refunded for payment intent {payment_intent_id}"
                )
                return {
                    "refund_id": donation.stripe_refund_id,
                    "amount_refunded": float(donation.amount_usd),
                    "status": "already_refunded",
                }

            # Check if donation was successful (can only refund successful payments)
            if donation.status != DonationStatus.SUCCEEDED.value:
                logger.warning(
                    f"Cannot refund donation {donation.id} with status {donation.status}"
                )
                return None

            # Create refund in Stripe
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                metadata={
                    "reason": reason,
                    "donation_id": str(donation.id),
                    "customer_email": donation.customer_email or "unknown",
                },
            )

            # Update donation status in database
            donation.status = "refunded"
            donation.stripe_refund_id = refund.id
            donation.message = f"Refunded: {reason}"
            db.commit()

            logger.info(
                f"Successfully refunded payment intent {payment_intent_id} for donation {donation.id} "
                f"(amount: ${donation.amount_usd}, customer: {donation.customer_email})"
            )

            return {
                "refund_id": refund.id,
                "amount_refunded": float(donation.amount_usd),
                "status": "refunded",
                "customer_email": donation.customer_email,
                "customer_name": donation.customer_name,
            }

        except stripe.error.StripeError as e:
            logger.error(
                f"Stripe error refunding payment intent {payment_intent_id}: {str(e)}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Error refunding payment intent {payment_intent_id}: {str(e)}"
            )
            db.rollback()
            return None

    def get_refund_status(self, refund_id: str) -> Optional[Dict]:
        """
        Get refund status from Stripe.

        Args:
            refund_id: Stripe refund ID

        Returns:
            Dict containing refund status or None if not found
        """
        try:
            refund = stripe.Refund.retrieve(refund_id)
            return {
                "id": refund.id,
                "amount": refund.amount,
                "currency": refund.currency,
                "status": refund.status,
                "reason": refund.reason,
                "metadata": refund.metadata,
                "created": refund.created,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving refund {refund_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving refund {refund_id}: {str(e)}")
            return None

    def refund_donation(
        self,
        db: Session,
        donation_id: int,
        amount_usd: Optional[float] = None,
        reason: str = "requested_by_customer",
    ) -> Dict:
        """
        Refund a donation by donation ID.

        Args:
            db: Database session
            donation_id: Database ID of the donation to refund
            amount_usd: Optional amount to refund (partial refund). If None, refunds full amount.
            reason: Reason for the refund (for Stripe metadata)

        Returns:
            Dict containing refund result with success status and details
        """
        try:
            # Get the donation
            donation = db.query(Donation).filter_by(id=donation_id).first()
            if not donation:
                return {"success": False, "error": f"Donation {donation_id} not found"}

            # Check if already refunded
            if donation.status == DonationStatus.REFUNDED.value:
                return {
                    "success": False,
                    "error": f"Donation {donation_id} is already refunded",
                }

            # Check if donation can be refunded
            if donation.status not in [DonationStatus.SUCCEEDED.value]:
                return {
                    "success": False,
                    "error": f"Cannot refund donation with status '{donation.status}'",
                }

            # Validate amount for partial refund
            if amount_usd is not None:
                if amount_usd <= 0:
                    return {
                        "success": False,
                        "error": "Invalid amount: must be positive",
                    }
                if amount_usd > float(donation.amount_usd):
                    return {
                        "success": False,
                        "error": f"Refund amount ${amount_usd} exceeds donation amount ${donation.amount_usd}",
                    }
                refund_amount_cents = int(amount_usd * 100)
            else:
                refund_amount_cents = int(float(donation.amount_usd) * 100)

            # Create refund in Stripe
            refund_params = {
                "payment_intent": donation.stripe_payment_intent_id,
                "reason": reason,
            }
            if amount_usd is not None:
                refund_params["amount"] = refund_amount_cents

            refund = stripe.Refund.create(**refund_params)

            # Update donation in database
            donation.status = DonationStatus.REFUNDED.value
            donation.stripe_refund_id = refund.id
            db.commit()

            logger.info(
                f"Successfully refunded donation {donation_id} (refund_id: {refund.id})"
            )

            return {
                "success": True,
                "refund_id": refund.id,
                "amount_usd": amount_usd or float(donation.amount_usd),
                "donation_id": donation_id,
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error refunding donation {donation_id}: {str(e)}")
            return {"success": False, "error": f"Stripe API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Database error refunding donation {donation_id}: {str(e)}")
            db.rollback()
            return {"success": False, "error": f"Database error: {str(e)}"}
