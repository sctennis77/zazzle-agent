"""
Interaction Agent Scheduler Module

This module runs the Reddit interaction agent on a schedule.
It can be run as a standalone service or as part of the Docker container.
"""

import logging
import os
import time
from datetime import datetime

import schedule
from sqlalchemy.orm import Session

from app.agents.reddit_interaction_agent import RedditInteractionAgent
from app.db.database import get_db, init_db
from app.db.models import ProductInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_interaction_job():
    """Run the interaction job and log results."""
    try:
        logger.info("Starting scheduled interaction job...")
        start_time = datetime.now()

        # Initialize database
        init_db()

        # Get database session
        db = next(get_db())

        # Initialize interaction agent
        agent = RedditInteractionAgent(db)

        # Find products with available actions
        products_with_actions = (
            db.query(ProductInfo)
            .filter(ProductInfo.interaction_actions.isnot(None))
            .all()
        )

        logger.info(
            f"Found {len(products_with_actions)} products with available actions"
        )

        interaction_count = 0
        for product in products_with_actions:
            try:
                # Check if product has any available actions
                if not product.interaction_actions:
                    continue

                # Process interactions for this product
                result = agent.process_interactions(str(product.id))

                if result:
                    interaction_count += 1
                    logger.info(f"Processed interactions for product {product.id}")
                else:
                    logger.warning(
                        f"No interactions processed for product {product.id}"
                    )

            except Exception as e:
                logger.error(
                    f"Error processing interactions for product {product.id}: {e}"
                )
                continue

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(
            f"Interaction job completed in {duration:.2f} seconds. "
            f"Processed {interaction_count} products."
        )

        db.close()

    except Exception as e:
        logger.error(f"Interaction job failed with error: {e}")
        logger.exception("Full traceback:")


def main():
    """Main scheduler function."""
    logger.info("Starting Interaction Agent Scheduler...")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    # Get schedule from environment variable (default: every 2 hours)
    schedule_cron = os.getenv("INTERACTION_SCHEDULE", "0 */2 * * *")

    # Parse cron schedule and set up job
    if schedule_cron == "0 */2 * * *":
        schedule.every(2).hours.do(run_interaction_job)
        logger.info("Interaction agent scheduled to run every 2 hours")
    elif schedule_cron == "0 */4 * * *":
        schedule.every(4).hours.do(run_interaction_job)
        logger.info("Interaction agent scheduled to run every 4 hours")
    elif schedule_cron == "0 */6 * * *":
        schedule.every(6).hours.do(run_interaction_job)
        logger.info("Interaction agent scheduled to run every 6 hours")
    else:
        # For testing, run every 10 minutes
        schedule.every(10).minutes.do(run_interaction_job)
        logger.info("Interaction agent scheduled to run every 10 minutes (test mode)")

    # Run initial job after startup
    logger.info("Running initial interaction job...")
    run_interaction_job()

    # Main scheduler loop
    logger.info("Interaction agent scheduler running...")
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Interaction agent scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(60)  # Wait before retrying


if __name__ == "__main__":
    main()
