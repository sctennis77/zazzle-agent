"""
Commission Worker for Kubernetes Jobs.

This module runs inside K8s Jobs to process commission tasks.
It handles the complete commission workflow from validation to completion.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import threading
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from app.affiliate_linker import ZazzleAffiliateLinker
from app.agents.reddit_agent import RedditAgent
from app.clients.imgur_client import ImgurClient
from app.config import REDIS_DB, REDIS_HOST, REDIS_PORT, WEBSOCKET_TASK_UPDATES_CHANNEL
from app.content_generator import ContentGenerator
from app.db.database import SessionLocal
from app.db.models import Donation, PipelineRun, PipelineTask, ProductInfo, RedditPost
from app.models import DonationStatus
from app.redis_service import redis_service
from app.services.commission_validator import CommissionValidator
from app.utils.logging_config import get_logger
from app.utils.openai_usage_tracker import log_session_summary
from app.zazzle_product_designer import ZazzleProductDesigner

logger = get_logger(__name__)


class CommissionWorker:
    """
    Worker class for processing commission tasks in K8s Jobs.

    This class handles the complete commission workflow:
    1. Validate commission parameters
    2. Find trending post
    3. Generate content
    4. Generate image
    5. Create Zazzle product
    6. Update donation status
    """

    def __init__(self, donation_id: int, task_data: Dict[str, Any]):
        """
        Initialize the commission worker.

        Args:
            donation_id: ID of the donation to process
            task_data: Task configuration data
        """
        self.donation_id = donation_id
        self.task_data = task_data
        self.db = SessionLocal()
        self.pipeline_task = None

        # Initialize pipeline configuration (same as old pipeline task runner)
        from app.models import PipelineConfig
        from app.zazzle_templates import ZAZZLE_PRINT_TEMPLATE

        # Get image quality from task data, default to standard
        image_quality = task_data.get("image_quality", "standard")

        self.config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id=ZAZZLE_PRINT_TEMPLATE.zazzle_template_id,
            zazzle_tracking_code=ZAZZLE_PRINT_TEMPLATE.zazzle_tracking_code,
            zazzle_affiliate_id=os.getenv("ZAZZLE_AFFILIATE_ID", ""),
            prompt_version="1.0.0",
            image_quality=image_quality,
        )

        # Initialize components with proper configuration
        self.reddit_agent = None  # Will be initialized per donation
        self.content_generator = ContentGenerator()
        self.zazzle_designer = ZazzleProductDesigner()
        self.affiliate_linker = ZazzleAffiliateLinker(
            zazzle_affiliate_id=os.getenv("ZAZZLE_AFFILIATE_ID", ""),
            zazzle_tracking_code=os.getenv("ZAZZLE_TRACKING_CODE", ""),
        )
        self.imgur_client = ImgurClient()

        logger.info(f"Commission worker initialized for donation {donation_id}")

    async def run(self) -> bool:
        """
        Run the complete commission workflow.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(
                f"Starting commission processing for donation {self.donation_id}"
            )

            # Step 1: Get donation
            donation = self._get_donation()
            if not donation:
                logger.error(f"Donation {self.donation_id} not found")
                return False
            self.donation = donation

            # Step 2: Get or create pipeline task
            self.pipeline_task = self._get_or_create_pipeline_task(donation)
            if not self.pipeline_task:
                logger.error(
                    f"Failed to get or create pipeline task for donation {self.donation_id}"
                )
                return False

            # Step 3: Mark task as in progress and send initial heartbeat
            self._update_task_status("in_progress")
            self._send_heartbeat()  # Ensure heartbeat is sent immediately

            # Step 4: Process commission (validation already done upstream)
            success = await self._process_commission(donation)

            # Step 5: Update task and donation status
            if success:
                self._update_task_status("completed")
            else:
                self._update_task_status("failed", "Commission processing failed")

            self._update_donation_status(donation, success)

            # Step 6: Log session summary
            logger.info(
                f"Commission processing complete for donation {self.donation_id} (user: {donation.customer_name}, tier: {donation.tier}, success: {success})"
            )
            log_session_summary()

            return success

        except Exception as e:
            logger.error(
                f"Commission processing failed for donation_id={self.donation_id}: {str(e)}\n{traceback.format_exc()}"
            )
            self._update_task_status("failed", str(e))
            self._update_donation_status(None, False, error=str(e))
            return False
        finally:
            self.db.close()

    def _get_donation(self) -> Optional[Donation]:
        """Get the donation from the database."""
        try:
            donation = self.db.query(Donation).filter_by(id=self.donation_id).first()
            if not donation:
                logger.error(f"Donation {self.donation_id} not found in database")
                return None

            logger.debug(
                f"Found donation: {donation.customer_name} - ${donation.amount_usd}"
            )
            return donation

        except Exception as e:
            logger.error(
                f"Error getting donation for donation_id={self.donation_id}: {str(e)}\n{traceback.format_exc()}"
            )
            return None

    def _get_or_create_pipeline_task(
        self, donation: Donation
    ) -> Optional[PipelineTask]:
        """Get or create a pipeline task for this commission."""
        try:
            # Look for existing task for this donation
            task = (
                self.db.query(PipelineTask).filter_by(donation_id=donation.id).first()
            )

            if not task:
                # Create new task
                subreddit_id = None
                if donation.subreddit:
                    subreddit_id = donation.subreddit.id
                elif donation.commission_type == "random_subreddit":
                    # Use "all" subreddit for random commissions
                    from app.subreddit_service import get_subreddit_service

                    subreddit_service = get_subreddit_service()
                    subreddit = subreddit_service.get_or_create_subreddit(
                        "all", self.db
                    )
                    subreddit_id = subreddit.id

                task = PipelineTask(
                    type="SUBREDDIT_POST",
                    subreddit_id=subreddit_id,
                    donation_id=donation.id,
                    priority=10,  # High priority for commissions
                    status="pending",
                    context_data=self.task_data,
                    created_at=datetime.now(),
                )

                self.db.add(task)
                self.db.commit()
                logger.debug(
                    f"Created new pipeline task {task.id} for donation {donation.id}"
                )
            else:
                logger.debug(
                    f"Found existing pipeline task {task.id} for donation {donation.id}"
                )

            return task

        except Exception as e:
            logger.error(
                f"Error getting or creating pipeline task for donation_id={donation.id}: {str(e)}\n{traceback.format_exc()}"
            )
            self.db.rollback()
            return None

    async def _publish_task_update_async(self, task_id: str, update: dict):
        """Publish task update using the async Redis service."""
        try:
            await redis_service.publish_task_update(task_id, update)
            logger.debug(f"[ASYNC REDIS] Published task update for {task_id}: {update}")
        except Exception as e:
            logger.error(
                f"[ASYNC REDIS] Failed to publish task update for task_id={task_id}: {str(e)}\n{traceback.format_exc()}"
            )

    def _update_task_status(
        self,
        status: str,
        error_message: str = None,
        progress: int = None,
        stage: str = None,
        message: str = None,
    ):
        try:
            if not self.pipeline_task:
                logger.warning(
                    f"No pipeline task to update for donation_id={self.donation_id}"
                )
                return
            self.pipeline_task.status = status

            # Update timing fields
            if status == "in_progress":
                if (
                    hasattr(self.pipeline_task, "started_at")
                    and not self.pipeline_task.started_at
                ):
                    self.pipeline_task.started_at = datetime.now()
                if hasattr(self.pipeline_task, "last_heartbeat"):
                    self.pipeline_task.last_heartbeat = datetime.now()
            elif status in ["completed", "failed"]:
                self.pipeline_task.completed_at = datetime.now()

            # Always update heartbeat for in_progress tasks
            if status == "in_progress" and hasattr(
                self.pipeline_task, "last_heartbeat"
            ):
                self.pipeline_task.last_heartbeat = datetime.now()

            if error_message:
                self.pipeline_task.error_message = error_message
            self.db.commit()
            # Remove duplicate logging - TaskManager handles status logs
            update = self._build_update_dict(
                status, error_message, progress, stage, message
            )
            if update:
                self._publish_task_update_simple(self.pipeline_task.id, update)
        except Exception as e:
            logger.error(
                f"Error updating task status for pipeline_task_id={getattr(self.pipeline_task, 'id', None)}: {str(e)}\n{traceback.format_exc()}"
            )
            self.db.rollback()

    def _publish_task_update_simple(self, task_id: str, update: dict):
        """Simple synchronous Redis publishing without event loop conflicts."""
        try:
            import json

            import redis

            from app.config import (
                REDIS_DB,
                REDIS_HOST,
                REDIS_PASSWORD,
                REDIS_PORT,
                REDIS_SSL,
            )

            # Create a simple Redis client for this operation
            r = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                ssl=REDIS_SSL,
                decode_responses=True,
            )
            # Create the message
            message = {
                "type": "task_update",
                "task_id": str(task_id),
                "data": update,
                "timestamp": datetime.now().isoformat(),
            }
            # Publish to Redis
            r.publish("task_updates", json.dumps(message))
            # Only log Redis publishing for errors or major status changes
            if update.get("status") in ["completed", "failed"] or logger.isEnabledFor(
                logging.DEBUG
            ):
                logger.debug(
                    f"Published update for task {task_id}: {update.get('status', 'unknown')}"
                )
        except Exception as e:
            logger.error(
                f"[SIMPLE REDIS] Failed to publish task update for task_id={task_id}: {str(e)}\n{traceback.format_exc()}"
            )

    def _build_update_dict(
        self,
        status: str,
        error_message: str = None,
        progress: int = None,
        stage: str = None,
        message: str = None,
    ) -> Optional[dict]:
        """Build the update dictionary for Redis publishing."""
        if not self.pipeline_task:
            return None

        update = {
            "status": status,
            "completed_at": (
                self.pipeline_task.completed_at.isoformat()
                if self.pipeline_task.completed_at
                else None
            ),
            "error": error_message,
            "reddit_username": self.donation.reddit_username,
            "tier": self.donation.tier,  # Fixed: removed .value since tier is already a string
            "subreddit": (
                self.donation.subreddit.subreddit_name
                if self.donation.subreddit
                else None
            ),
            "amount_usd": float(self.donation.amount_usd),
            "is_anonymous": self.donation.is_anonymous,
            "progress": progress,
            "stage": stage,
            "message": message,
        }
        return update

    async def _process_commission(self, donation: Donation) -> bool:
        """Process the commission workflow."""
        try:
            logger.info(
                f"Processing commission workflow for donation_id={donation.id}, user={donation.customer_name}, tier={donation.tier}"
            )

            # Step 1: Find trending post and generate product
            product_info = await self._generate_product(donation)
            if not product_info:
                logger.error(
                    f"Failed to generate product for donation_id={donation.id}"
                )
                return False

            # Step 2: Create Zazzle product
            zazzle_result = await self._create_zazzle_product(product_info, donation)
            if not zazzle_result:
                logger.error(
                    f"Failed to create Zazzle product for donation_id={donation.id}"
                )
                return False

            # Step 3: Save product to database
            self._save_product(product_info, donation)

            # Step 4: Broadcast commission completion (100%)
            await self._broadcast_commission_complete(donation, product_info)

            logger.info(
                f"Commission processing completed successfully for donation_id={donation.id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error processing commission for donation_id={donation.id}: {str(e)}\n{traceback.format_exc()}"
            )
            return False

    async def _generate_product(self, donation: Donation) -> Optional[ProductInfo]:
        """Generate product from Reddit post."""
        try:
            logger.info("Generating product from Reddit post")

            # Get subreddit and post_id from donation
            subreddit_name = (
                donation.subreddit.subreddit_name if donation.subreddit else None
            )
            post_id = donation.post_id

            if not subreddit_name or not post_id:
                logger.error(
                    f"Missing subreddit or post_id in donation: subreddit={subreddit_name}, post_id={post_id}"
                )
                return None

            logger.info(f"Generating product for r/{subreddit_name} post {post_id}")

            # Initialize RedditAgent with proper configuration (same as old pipeline task runner)
            self.reddit_agent = RedditAgent(
                config=self.config,
                pipeline_run_id=None,  # Will be set by pipeline
                session=self.db,
                subreddit_name=subreddit_name,
                task_context={"post_id": post_id, "subreddit": subreddit_name},
                progress_callback=self._progress_callback,
            )

            # Generate product with detailed progress updates
            product_info = await self._generate_product_with_progress(donation)
            if not product_info:
                logger.error("Failed to generate product from Reddit post")
                return None

            logger.info(f"Generated product: {product_info.theme}")
            return product_info

        except Exception as e:
            logger.error(f"Error generating product: {e}")
            return None

    async def _generate_product_with_progress(
        self, donation: Donation
    ) -> Optional[ProductInfo]:
        """Generate product with progress updates."""
        try:
            # Step 1: Broadcast post fetch started (10%)
            await self._broadcast_post_fetch_started(donation)

            # Step 2: Generate the actual product (this includes all progress callbacks)
            product_info = await self.reddit_agent.find_and_create_product_for_task()
            if not product_info:
                return None

            # Step 3: Broadcast Zazzle creation started (95%)
            await self._broadcast_zazzle_creation_started(donation)

            # Step 4: Broadcast Zazzle creation complete (97%)
            await self._broadcast_zazzle_creation_complete(donation)

            # Step 5: Broadcast commission complete (100%)
            await self._broadcast_commission_complete(donation, product_info)

            return product_info

        except Exception as e:
            logger.error(f"Error in product generation with progress: {e}")
            return None

    async def _broadcast_post_fetch_started(self, donation: Donation):
        self._update_task_status(
            status="in_progress",
            progress=10,
            stage="post_fetching",
            message=f"Fetching commissioned post from r/{donation.subreddit.subreddit_name if donation.subreddit else 'unknown'}",
        )

    async def _broadcast_zazzle_creation_started(self, donation: Donation):
        self._update_task_status(
            status="in_progress",
            progress=95,
            stage="zazzle_creation_started",
            message="Creating product on Zazzle...",
        )

    async def _broadcast_zazzle_creation_complete(self, donation: Donation):
        self._update_task_status(
            status="in_progress",
            progress=97,
            stage="zazzle_creation_complete",
            message="Product created on Zazzle successfully",
        )

    async def _broadcast_commission_complete(
        self, donation: Donation, product_info: ProductInfo
    ):
        post_title = "Unknown Post"
        if hasattr(product_info, "reddit_context") and product_info.reddit_context:
            post_title = product_info.reddit_context.post_title
        self._update_task_status(
            status="in_progress",
            progress=100,
            stage="commission_complete",
            message=f"Commission finished: Illustrated {post_title}",
        )

    async def _create_zazzle_product(
        self, product_info: ProductInfo, donation: Donation
    ) -> bool:
        """Create product on Zazzle."""
        try:
            logger.info("Creating Zazzle product")

            # The product_info already contains the design_instructions and reddit_context
            # from the RedditAgent.find_and_create_product_for_task() call
            # We don't need to create a new Zazzle product since it was already created
            # Just verify the product was created successfully
            if not product_info or not product_info.product_url:
                logger.error("Product info is missing or incomplete")
                return False

            logger.info(f"Zazzle product already created: {product_info.product_url}")
            return True

        except Exception as e:
            logger.error(f"Error with Zazzle product: {e}")
            return False

    def _save_product(self, product_info: ProductInfo, donation: Donation):
        """Save product to database."""
        try:
            logger.info("Saving product to database")
            from app.db.mappers import product_info_to_db, reddit_context_to_db
            from app.db.models import PipelineRun
            from app.pipeline_status import PipelineStatus

            pipeline_run = PipelineRun(
                status="completed",  # Use simple string status
                summary=f"Commission for donation {donation.id}",
                config={"commission": True, "donation_id": donation.id},
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=0,
                version="1.0.0",
            )
            self.db.add(pipeline_run)
            self.db.flush()  # Get the ID without committing

            # Link the pipeline task to the new pipeline run
            if self.pipeline_task:
                self.pipeline_task.pipeline_run_id = pipeline_run.id
                self.db.commit()

            # Create RedditPost from the product's reddit_context
            reddit_context = getattr(product_info, "reddit_context", None)
            if reddit_context is None:
                logger.error(
                    "No reddit_context found in product_info; cannot create RedditPost for commission."
                )
                self.db.rollback()
                return
            db_reddit_post = reddit_context_to_db(
                reddit_context, pipeline_run.id, self.db
            )
            self.db.add(db_reddit_post)
            self.db.flush()  # Get the ID without committing

            # Create the database product info with the pipeline run ID and reddit post ID
            db_product_info = product_info_to_db(
                product_info,
                pipeline_run_id=pipeline_run.id,
                reddit_post_id=db_reddit_post.id,
            )

            # Store donation info in design_description for tracking
            donation_info = (
                f"Commission for donation {donation.id} - {donation.customer_name}"
            )
            if db_product_info.design_description:
                db_product_info.design_description = (
                    f"{db_product_info.design_description}\n\n{donation_info}"
                )
            else:
                db_product_info.design_description = donation_info

            # Save to database
            self.db.add(db_product_info)
            self.db.commit()

            logger.info(
                f"Saved product to database with ID: {db_product_info.id} (pipeline run: {pipeline_run.id}, reddit post: {db_reddit_post.id})"
            )

        except Exception as e:
            logger.error(f"Error saving product: {e}")
            self.db.rollback()

    def _update_donation_status(
        self, donation: Donation, success: bool, error: str = None
    ):
        """Update donation status."""
        try:
            from app.models import DonationStatus

            if success:
                donation.status = "succeeded"
                logger.info(f"Updated donation {self.donation_id} status to SUCCEEDED")
            else:
                donation.status = "failed"
                if error:
                    donation.message = f"Commission failed: {error}"
                logger.error(f"Updated donation {self.donation_id} status to FAILED")
            self.db.commit()
        except Exception as e:
            logger.error(f"Error updating donation status: {e}")
            self.db.rollback()

    def _send_heartbeat(self):
        """Send a heartbeat to indicate the task is still running."""
        try:
            if self.pipeline_task and hasattr(self.pipeline_task, "last_heartbeat"):
                self.pipeline_task.last_heartbeat = datetime.now()
                self.db.commit()
                logger.debug(f"Sent heartbeat for task {self.pipeline_task.id}")
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            self.db.rollback()

    async def _progress_callback(self, stage: str, data: dict):
        """Callback for RedditAgent progress updates."""
        try:
            logger.debug(
                f"Progress callback: {stage} ({data.get('progress', 'no progress')}%)"
            )

            # Send heartbeat on every progress update
            self._send_heartbeat()

            if stage == "post_fetched":
                post_title = data.get("post_title", "Unknown Post")
                self._update_task_status(
                    status="in_progress",
                    progress=20,
                    stage="post_fetched",
                    message=f"Fetched commissioned post: {post_title}",
                )

            elif stage == "product_designed":
                theme = data.get("theme", "Unknown Theme")
                self._update_task_status(
                    status="in_progress",
                    progress=30,
                    stage="product_designed",
                    message=f"Product design created: {theme}",
                )

            elif stage == "image_generation_started":
                post_id = data.get("post_id", "unknown")
                subreddit_name = data.get("subreddit_name", "unknown")
                self._update_task_status(
                    status="in_progress",
                    progress=40,
                    stage="image_generation_started",
                    message=f"Clouvel started working on {post_id} from r/{subreddit_name}",
                )

            elif stage == "image_generation_progress":
                progress = data.get("progress", 40)
                self._update_task_status(
                    status="in_progress",
                    progress=progress,
                    stage="image_generation_in_progress",
                    message=f"Clouvel illustrating ...  ({progress}%)",
                )

            elif stage == "image_generation_complete":
                self._update_task_status(
                    status="in_progress",
                    progress=90,
                    stage="image_generated",
                    message="Image generated successfully",
                )

            else:
                logger.warning(f"Unknown progress stage: {stage}")

        except Exception as e:
            logger.error(f"Error in progress callback for stage {stage}: {e}")
            # Don't let callback errors break the main workflow


def main():
    """Main entry point for the commission worker."""
    parser = argparse.ArgumentParser(description="Commission Worker")
    parser.add_argument(
        "--donation-id", type=int, required=True, help="Donation ID to process"
    )
    parser.add_argument(
        "--task-data", type=str, required=True, help="Task data as JSON string"
    )

    args = parser.parse_args()

    try:
        # Parse task data
        task_data = json.loads(args.task_data)

        # Create and run worker
        worker = CommissionWorker(args.donation_id, task_data)
        success = asyncio.run(worker.run())

        if success:
            logger.info("Commission worker completed successfully")
            sys.exit(0)
        else:
            logger.error("Commission worker failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Commission worker error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
