import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.redis_service import redis_service
from app.services.scheduler_service import SchedulerService
from app.task_manager import TaskManager

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """Background scheduler that runs scheduled commissions in a loop."""

    def __init__(self):
        self.scheduler_service: Optional[SchedulerService] = None
        self.task_manager: Optional[TaskManager] = None
        self.running = False
        self.check_interval = 300  # Check every 5 minutes

    async def initialize(self) -> None:
        """Initialize the scheduler with dependencies."""
        # Import here to avoid circular imports
        from app.api import task_manager

        self.task_manager = task_manager
        self.scheduler_service = SchedulerService(redis_service, task_manager)
        logger.info("Background scheduler initialized")

    async def start(self) -> None:
        """Start the background scheduler loop."""
        if not self.scheduler_service:
            await self.initialize()

        self.running = True
        logger.info("Starting background scheduler")

        while self.running:
            try:
                await self._check_and_run_scheduled_commission()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in background scheduler: {e}")
                # Continue running even if there's an error
                await asyncio.sleep(self.check_interval)

    async def stop(self) -> None:
        """Stop the background scheduler."""
        self.running = False
        logger.info("Background scheduler stopped")

    async def _check_and_run_scheduled_commission(self) -> None:
        """Check if we should run a scheduled commission and execute it."""
        async with self._get_db_session() as db:
            try:
                # Check if we should run
                should_run = (
                    await self.scheduler_service.should_run_scheduled_commission(db)
                )

                if should_run:
                    logger.info("Running scheduled commission")
                    result = await self.scheduler_service.run_scheduled_commission(db)

                    if result:
                        logger.info(f"Scheduled commission completed: {result}")
                    else:
                        logger.info(
                            "Scheduled commission skipped (another instance running)"
                        )
                else:
                    logger.debug("Scheduled commission not due yet")

            except Exception as e:
                logger.error(f"Error checking/running scheduled commission: {e}")

    @asynccontextmanager
    async def _get_db_session(self):
        """Get a database session with proper cleanup."""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


# Global background scheduler instance
background_scheduler = BackgroundScheduler()
