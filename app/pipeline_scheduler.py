"""
Pipeline Scheduler Module

This module runs the product generation pipeline on a schedule.
It can be run as a standalone service or as part of the Docker container.
"""

import asyncio
import logging
import os
import time
from datetime import datetime

import schedule

from app.db.database import init_db
from app.main import run_full_pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_pipeline_job():
    """Run the pipeline job and log results."""
    try:
        logger.info("Starting scheduled pipeline run...")
        start_time = datetime.now()

        # Run the pipeline
        result = await run_full_pipeline()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        if result:
            logger.info(f"Pipeline completed successfully in {duration:.2f} seconds")
        else:
            logger.error(f"Pipeline failed after {duration:.2f} seconds")

    except Exception as e:
        logger.error(f"Pipeline job failed with error: {e}")
        logger.exception("Full traceback:")


def run_pipeline_job_sync():
    """Synchronous wrapper for the async pipeline job."""
    asyncio.run(run_pipeline_job())


def main():
    """Main scheduler function."""
    logger.info("Starting Pipeline Scheduler...")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    # Get schedule from environment variable (default: every 6 hours)
    schedule_cron = os.getenv("PIPELINE_SCHEDULE", "0 */6 * * *")

    # Parse cron schedule and set up job
    if schedule_cron == "0 */6 * * *":
        schedule.every(6).hours.do(run_pipeline_job_sync)
        logger.info("Pipeline scheduled to run every 6 hours")
    elif schedule_cron == "0 */12 * * *":
        schedule.every(12).hours.do(run_pipeline_job_sync)
        logger.info("Pipeline scheduled to run every 12 hours")
    elif schedule_cron == "0 */24 * * *":
        schedule.every(24).hours.do(run_pipeline_job_sync)
        logger.info("Pipeline scheduled to run every 24 hours")
    else:
        # For testing, run every 5 minutes
        schedule.every(5).minutes.do(run_pipeline_job_sync)
        logger.info("Pipeline scheduled to run every 5 minutes (test mode)")

    # Run initial job after startup
    logger.info("Running initial pipeline job...")
    run_pipeline_job_sync()

    # Main scheduler loop
    logger.info("Pipeline scheduler running...")
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Pipeline scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(60)  # Wait before retrying


if __name__ == "__main__":
    main()
