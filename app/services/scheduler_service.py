import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.api import get_image_quality_for_tier
from app.db.models import Donation, SchedulerConfig, SourceType
from app.models import DonationStatus, DonationTier, TIER_AMOUNTS
from app.redis_service import RedisService
from app.subreddit_service import get_subreddit_service
from app.task_manager import TaskManager

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled bronze tier commissions."""

    def __init__(self, redis_service: RedisService, task_manager: TaskManager):
        self.redis_service = redis_service
        self.task_manager = task_manager
        self.lock_key = "scheduler:commission_lock"
        self.lock_timeout = 300  # 5 minutes lock timeout

    async def should_run_scheduled_commission(self, db: Session) -> bool:
        """Check if we should run a scheduled commission."""
        config = self._get_scheduler_config(db)
        if not config or not config.enabled:
            return False

        now = datetime.now(timezone.utc)

        # If no last run, we should run
        if not config.last_run_at:
            return True

        # Check if enough time has passed since last run
        # Ensure timezone-aware comparison
        last_run_time = config.last_run_at
        if last_run_time.tzinfo is None:
            last_run_time = last_run_time.replace(tzinfo=timezone.utc)
        
        next_run_time = last_run_time + timedelta(hours=config.interval_hours)
        return now >= next_run_time

    async def run_scheduled_commission(self, db: Session) -> Optional[dict]:
        """
        Execute a scheduled bronze tier commission with distributed locking.
        Returns commission details if created, None if skipped.
        """
        return await self._run_commission_with_lock(db, check_interval=True)

    async def run_manual_commission(self, db: Session) -> Optional[dict]:
        """
        Execute a manual bronze tier commission with distributed locking.
        Bypasses interval checks for manual triggers.
        Returns commission details if created, None if skipped.
        """
        return await self._run_commission_with_lock(db, check_interval=False)

    async def _run_commission_with_lock(self, db: Session, check_interval: bool = True) -> Optional[dict]:
        """
        Execute a bronze tier commission with distributed locking.
        Returns commission details if created, None if skipped.
        """
        # Try to acquire distributed lock
        lock_acquired = await self.redis_service.acquire_lock(
            self.lock_key, self.lock_timeout
        )

        if not lock_acquired:
            logger.info("Commission skipped - another instance is running")
            return None

        try:
            # Check if we should run (only for scheduled, not manual)
            if check_interval and not await self.should_run_scheduled_commission(db):
                logger.info("Scheduled commission no longer needed")
                return None

            # Create the commission
            commission_data = await self._create_scheduled_commission(db)

            # Update scheduler config (only for scheduled runs)
            if check_interval:
                self._update_scheduler_last_run(db)

            logger.info(f"Commission created: {commission_data}")
            return commission_data

        except Exception as e:
            logger.error(f"Error in commission: {e}")
            raise
        finally:
            # Always release the lock
            await self.redis_service.release_lock(self.lock_key)

    async def _create_scheduled_commission(self, db: Session) -> dict:
        """Create a bronze tier commission for a random subreddit following validation pattern."""
        # Step 1: Pick random subreddit using the same logic as other commissions
        from app.agents.reddit_agent import pick_subreddit

        subreddit_name = pick_subreddit(db)

        # Step 2: Validate the commission using the same validator as API endpoints
        from app.services.commission_validator import CommissionValidator

        validator = CommissionValidator(session=db)

        # Validate the random subreddit commission
        validation_result = await validator.validate_commission(
            commission_type="random_subreddit",
            subreddit=subreddit_name,
            post_id=None,
            post_url=None,
        )

        if not validation_result.valid:
            # If validation fails, log and raise exception
            logger.error(
                f"Scheduled commission validation failed for r/{subreddit_name}: {validation_result.error}"
            )
            raise Exception(f"Commission validation failed: {validation_result.error}")

        # Step 3: Get or create subreddit in database (same as other flows)
        subreddit_service = get_subreddit_service()
        subreddit = subreddit_service.get_or_create_subreddit(subreddit_name, db)

        # Create fake payment intent ID
        payment_intent_id = f"scheduled-{uuid.uuid4()}"

        # Bronze tier configuration
        tier = DonationTier.BRONZE
        amount_usd = float(TIER_AMOUNTS[tier])  # Use enum-defined amount

        # Create donation entry
        donation = Donation(
            stripe_payment_intent_id=payment_intent_id,
            amount_cents=int(amount_usd * 100),
            amount_usd=amount_usd,
            currency="usd",
            status=DonationStatus.SUCCEEDED.value,
            tier=tier.value,
            customer_email=None,
            customer_name="Clouvel",  # Fixed donor name
            message=None,
            subreddit_id=subreddit.id,
            reddit_username="clouvel",
            stripe_metadata=None,
            is_anonymous=False,
            donation_type="commission",
            commission_type="random_subreddit",  # Random subreddit selection
            post_id=validation_result.post_id,  # Use validated post ID
            commission_message=None,
            source=SourceType.MANUAL,  # Manual source for scheduled commissions
        )

        db.add(donation)
        db.commit()
        db.refresh(donation)

        # Prepare task data
        task_data = {
            "donation_id": donation.id,
            "donation_amount": float(donation.amount_usd),
            "tier": donation.tier,
            "customer_name": donation.customer_name,
            "reddit_username": donation.reddit_username,
            "is_anonymous": donation.is_anonymous,
            "donation_type": donation.donation_type,
            "commission_type": donation.commission_type,
            "commission_message": donation.commission_message,
            "post_id": donation.post_id,
            "image_quality": get_image_quality_for_tier(donation.tier),
        }

        # Create commission task
        task_id = self.task_manager.create_commission_task(donation.id, task_data, db)

        return {
            "donation_id": donation.id,
            "task_id": task_id,
            "subreddit": subreddit.subreddit_name,
            "amount_usd": amount_usd,
            "tier": tier.value,
            "created_at": donation.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "validated_post_id": validation_result.post_id,
            "validation_score": getattr(validation_result, "score", None),
        }

    def _get_scheduler_config(self, db: Session) -> Optional[SchedulerConfig]:
        """Get the scheduler configuration."""
        return db.query(SchedulerConfig).first()

    def _update_scheduler_last_run(self, db: Session) -> None:
        """Update the last run timestamp in scheduler config."""
        config = self._get_scheduler_config(db)
        now = datetime.now(timezone.utc)

        if config:
            config.last_run_at = now
            config.next_run_at = now + timedelta(hours=config.interval_hours)
            config.updated_at = now
        else:
            # Create initial config if it doesn't exist
            config = SchedulerConfig(
                enabled=True,
                interval_hours=24,
                last_run_at=now,
                next_run_at=now + timedelta(hours=24),
            )
            db.add(config)

        db.commit()

    def get_scheduler_status(self, db: Session) -> dict:
        """Get current scheduler status and configuration."""
        config = self._get_scheduler_config(db)
        if not config:
            return {
                "enabled": False,
                "interval_hours": 24,
                "last_run_at": None,
                "next_run_at": None,
            }

        return {
            "enabled": config.enabled,
            "interval_hours": config.interval_hours,
            "last_run_at": (
                config.last_run_at.replace(tzinfo=timezone.utc).isoformat() if config.last_run_at else None
            ),
            "next_run_at": (
                config.next_run_at.replace(tzinfo=timezone.utc).isoformat() if config.next_run_at else None
            ),
        }

    def update_scheduler_config(
        self, db: Session, enabled: bool, interval_hours: int
    ) -> dict:
        """Update scheduler configuration."""
        config = self._get_scheduler_config(db)
        now = datetime.now(timezone.utc)

        if config:
            config.enabled = enabled
            config.interval_hours = interval_hours
            config.updated_at = now
            # Recalculate next run time if enabled and we have a last run
            if enabled and config.last_run_at:
                config.next_run_at = config.last_run_at + timedelta(
                    hours=interval_hours
                )
        else:
            # Create new config
            config = SchedulerConfig(
                enabled=enabled,
                interval_hours=interval_hours,
                last_run_at=None,
                next_run_at=None,
            )
            db.add(config)

        db.commit()
        db.refresh(config)

        return {
            "enabled": config.enabled,
            "interval_hours": config.interval_hours,
            "last_run_at": (
                config.last_run_at.replace(tzinfo=timezone.utc).isoformat() if config.last_run_at else None
            ),
            "next_run_at": (
                config.next_run_at.replace(tzinfo=timezone.utc).isoformat() if config.next_run_at else None
            ),
        }
