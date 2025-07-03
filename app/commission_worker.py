"""
Commission Worker for Kubernetes Jobs.

This module runs inside K8s Jobs to process commission tasks.
It handles the complete commission workflow from validation to completion.
"""

import argparse
import json
import logging
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import time
import redis.asyncio as redis
import threading

from app.agents.reddit_agent import RedditAgent
from app.content_generator import ContentGenerator
from app.image_generator import ImageGenerator
from app.zazzle_product_designer import ZazzleProductDesigner
from app.affiliate_linker import ZazzleAffiliateLinker
from app.clients.imgur_client import ImgurClient
from app.db.database import SessionLocal
from app.db.models import Donation, ProductInfo, PipelineTask, PipelineRun, RedditPost
from app.models import DonationStatus
from app.services.commission_validator import CommissionValidator
from app.utils.logging_config import get_logger
from app.utils.openai_usage_tracker import log_session_summary
from app.redis_service import redis_service
from app.config import WEBSOCKET_TASK_UPDATES_CHANNEL, REDIS_HOST, REDIS_PORT, REDIS_DB

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
        
        self.config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id=ZAZZLE_PRINT_TEMPLATE.zazzle_template_id,
            zazzle_tracking_code=ZAZZLE_PRINT_TEMPLATE.zazzle_tracking_code,
            zazzle_affiliate_id=os.getenv("ZAZZLE_AFFILIATE_ID", ""),
            prompt_version="1.0.0",
        )
        
        # Initialize components with proper configuration
        self.reddit_agent = None  # Will be initialized per donation
        self.content_generator = ContentGenerator()
        self.image_generator = ImageGenerator(model=self.config.model)
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
            logger.info(f"Starting commission processing for donation {self.donation_id}")
            
            # Step 1: Get donation
            donation = self._get_donation()
            if not donation:
                logger.error(f"Donation {self.donation_id} not found")
                return False
            self.donation = donation
            
            # Step 2: Get or create pipeline task
            self.pipeline_task = self._get_or_create_pipeline_task(donation)
            if not self.pipeline_task:
                logger.error("Failed to get or create pipeline task")
                return False
            
            # Step 3: Mark task as in progress
            self._update_task_status("in_progress")
            
            # Step 4: Process commission (validation already done upstream)
            success = await self._process_commission(donation)
            
            # Step 5: Update task and donation status
            if success:
                self._update_task_status("completed")
            else:
                self._update_task_status("failed", "Commission processing failed")
            
            self._update_donation_status(donation, success)
            
            # Step 6: Log session summary
            log_session_summary()
            
            return success
            
        except Exception as e:
            logger.error(f"Commission processing failed: {e}")
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
            
            logger.info(f"Found donation: {donation.customer_name} - ${donation.amount_usd}")
            return donation
            
        except Exception as e:
            logger.error(f"Error getting donation: {e}")
            return None
    
    def _get_or_create_pipeline_task(self, donation: Donation) -> Optional[PipelineTask]:
        """Get or create a pipeline task for this commission."""
        try:
            # Look for existing task for this donation
            task = self.db.query(PipelineTask).filter_by(donation_id=donation.id).first()
            
            if not task:
                # Create new task
                subreddit_id = None
                if donation.subreddit:
                    subreddit_id = donation.subreddit.id
                elif donation.commission_type == "random_subreddit":
                    # Use "all" subreddit for random commissions
                    from app.subreddit_service import get_subreddit_service
                    subreddit_service = get_subreddit_service()
                    subreddit = subreddit_service.get_or_create_subreddit("all", self.db)
                    subreddit_id = subreddit.id
                
                task = PipelineTask(
                    type="SUBREDDIT_POST",
                    subreddit_id=subreddit_id,
                    donation_id=donation.id,
                    priority=10,  # High priority for commissions
                    status="pending",
                    context_data=self.task_data,
                    created_at=datetime.now()
                )
                
                self.db.add(task)
                self.db.commit()
                logger.info(f"Created new pipeline task {task.id} for donation {donation.id}")
            else:
                logger.info(f"Found existing pipeline task {task.id} for donation {donation.id}")
            
            return task
            
        except Exception as e:
            logger.error(f"Error getting or creating pipeline task: {e}")
            self.db.rollback()
            return None
    
    def _publish_task_update_sync(self, task_id: str, update: dict):
        try:
            client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
            message = json.dumps({
                "type": "task_update",
                "task_id": task_id,
                "data": update,
                "timestamp": time.time(),
            })
            client.publish(WEBSOCKET_TASK_UPDATES_CHANNEL, message)
            client.close()
            logger.info(f"[SYNC REDIS] Published task update for {task_id}: {update}")
        except Exception as e:
            logger.error(f"[SYNC REDIS] Failed to publish task update: {e}")

    def _build_update_dict(self, status: str, error_message: str = None, progress: int = None, stage: str = None, message: str = None):
        if not self.pipeline_task:
            logger.warning("No pipeline task to update")
            return None
        donation = self.pipeline_task.donation
        subreddit = self.pipeline_task.subreddit
        update = {
            "status": status,
            "completed_at": self.pipeline_task.completed_at.isoformat() if self.pipeline_task.completed_at else None,
            "error": error_message or self.pipeline_task.error_message,
            "reddit_username": donation.reddit_username if donation and donation.reddit_username and not donation.is_anonymous else "Anonymous",
            "tier": donation.tier if donation else None,
            "subreddit": subreddit.subreddit_name if subreddit else None,
            "amount_usd": float(donation.amount_usd) if donation else None,
            "is_anonymous": donation.is_anonymous if donation else None,
            "progress": progress if progress is not None else (100 if status == "completed" else 0),
            "stage": stage if stage is not None else ("commission_complete" if status == "completed" else status),
            "message": message if message is not None else ("Commission completed successfully" if status == "completed" else "Processing commission..."),
        }
        return update

    def _update_task_status(self, status: str, error_message: str = None, progress: int = None, stage: str = None, message: str = None):
        try:
            if not self.pipeline_task:
                logger.warning("No pipeline task to update")
                return
            self.pipeline_task.status = status
            if status in ["completed", "failed"]:
                self.pipeline_task.completed_at = datetime.now()
            if error_message:
                self.pipeline_task.error_message = error_message
            self.db.commit()
            logger.info(f"Updated pipeline task {self.pipeline_task.id} status to {status}")
            update = self._build_update_dict(status, error_message, progress, stage, message)
            if update is not None:
                self._publish_task_update_sync(str(self.pipeline_task.id), update)
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            self.db.rollback()
    
    async def _process_commission(self, donation: Donation) -> bool:
        """Process the commission workflow."""
        try:
            logger.info("Processing commission workflow")
            
            # Step 1: Find trending post and generate product
            product_info = await self._generate_product(donation)
            if not product_info:
                logger.error("Failed to generate product")
                return False
            
            # Step 2: Create Zazzle product
            zazzle_result = await self._create_zazzle_product(product_info, donation)
            if not zazzle_result:
                logger.error("Failed to create Zazzle product")
                return False
            
            # Step 3: Save product to database
            self._save_product(product_info, donation)
            
            # Broadcast commission completion
            await self._broadcast_commission_complete(donation, product_info)
            
            logger.info("Commission processing completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error processing commission: {e}")
            return False
    
    async def _generate_product(self, donation: Donation) -> Optional[ProductInfo]:
        """Generate product from Reddit post."""
        try:
            logger.info("Generating product from Reddit post")
            
            # Get subreddit and post_id from donation
            subreddit_name = donation.subreddit.subreddit_name if donation.subreddit else None
            post_id = donation.post_id
            
            if not subreddit_name or not post_id:
                logger.error(f"Missing subreddit or post_id in donation: subreddit={subreddit_name}, post_id={post_id}")
                return None
            
            logger.info(f"Generating product for r/{subreddit_name} post {post_id}")
            
            # Initialize RedditAgent with proper configuration (same as old pipeline task runner)
            self.reddit_agent = RedditAgent(
                config=self.config,
                pipeline_run_id=None,  # Will be set by pipeline
                session=self.db,
                subreddit_name=subreddit_name,
                task_context={
                    'post_id': post_id,
                    'subreddit': subreddit_name
                },
                progress_callback=self._progress_callback
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
    
    async def _generate_product_with_progress(self, donation: Donation) -> Optional[ProductInfo]:
        """Generate product with detailed progress updates."""
        try:
            # Step 1: Fetch the post
            post_info = await self._fetch_post_with_progress(donation)
            if not post_info:
                return None
            
            # Step 2: Generate product idea
            product_idea = await self._generate_product_idea_with_progress(post_info)
            if not product_idea:
                return None
            
            # Step 3: Generate image
            product_info = await self._generate_image_with_progress(product_idea, donation)
            if not product_info:
                return None
            
            return product_info
            
        except Exception as e:
            logger.error(f"Error in product generation with progress: {e}")
            return None
    
    async def _fetch_post_with_progress(self, donation: Donation) -> Optional[dict]:
        """Fetch the Reddit post with progress update."""
        try:
            # This will trigger the post fetching in RedditAgent
            # The actual fetch happens in _find_trending_post_for_task
            # We'll broadcast after the post is fetched
            
            # For now, we'll broadcast when we start the fetch process
            await self._broadcast_post_fetch_started(donation)
            
            # The actual post fetching happens in the RedditAgent
            # We'll need to modify the RedditAgent to call back to us
            # For now, we'll assume the post is fetched successfully
            
            return {
                'post_id': donation.post_id,
                'subreddit': donation.subreddit.subreddit_name if donation.subreddit else None
            }
            
        except Exception as e:
            logger.error(f"Error fetching post: {e}")
            return None
    
    async def _generate_product_idea_with_progress(self, post_info: dict) -> Optional[dict]:
        """Generate product idea with progress update."""
        try:
            # This will trigger the product idea generation in RedditAgent
            # We'll broadcast when the product idea is generated
            
            # For now, we'll assume the product idea is generated successfully
            # The actual generation happens in _determine_product_idea
            
            return {
                'post_id': post_info['post_id'],
                'subreddit': post_info['subreddit']
            }
            
        except Exception as e:
            logger.error(f"Error generating product idea: {e}")
            return None
    
    async def _generate_image_with_progress(self, product_idea: dict, donation: Donation) -> Optional[ProductInfo]:
        """Generate image with progress updates."""
        try:
            # Step 1: Broadcast image generation start
            await self._broadcast_image_generation_started(product_idea, donation)
            
            # Step 2: Generate the actual product (this includes image generation)
            product_info = await self.reddit_agent.find_and_create_product_for_task()
            if not product_info:
                return None
            
            # Step 3: Broadcast image generation complete
            await self._broadcast_image_generation_complete(product_info, donation)
            
            # Step 4: Broadcast image stamping complete
            await self._broadcast_image_stamping_complete(donation)
            
            return product_info
            
        except Exception as e:
            logger.error(f"Error generating image with progress: {e}")
            return None
    
    async def _broadcast_post_fetch_started(self, donation: Donation):
        self._update_task_status(
            status="in_progress",
            progress=10,
            stage="post_fetching",
            message=f"Fetching commissioned post from r/{donation.subreddit.subreddit_name if donation.subreddit else 'unknown'}"
        )
    
    async def _broadcast_post_fetched(self, donation: Donation, post_title: str):
        self._update_task_status(
            status="in_progress",
            progress=20,
            stage="post_fetched",
            message=f"Fetched commissioned post: {post_title}"
        )
    
    async def _broadcast_product_designed(self, product_info: ProductInfo, donation: Donation):
        self._update_task_status(
            status="in_progress",
            progress=40,
            stage="product_designed",
            message=f"Product design created: {product_info.theme}"
        )
    
    async def _broadcast_image_generation_started(self, product_idea: dict, donation: Donation):
        self._update_task_status(
            status="in_progress",
            progress=50,
            stage="image_generation_started",
            message="Generating image with DALL-E..."
        )
    
    async def _broadcast_image_generation_complete(self, product_info: ProductInfo, donation: Donation):
        self._update_task_status(
            status="in_progress",
            progress=80,
            stage="image_generated",
            message="Image generated successfully"
        )
    
    async def _broadcast_image_stamping_complete(self, donation: Donation):
        customer_name = donation.customer_name if donation.customer_name else "Anonymous"
        self._update_task_status(
            status="in_progress",
            progress=90,
            stage="image_stamped",
            message=f"Image stamped with QR code for {customer_name}"
        )
    
    async def _broadcast_commission_complete(self, donation: Donation, product_info: ProductInfo):
        post_title = "Unknown Post"
        if hasattr(product_info, 'reddit_context') and product_info.reddit_context:
            post_title = product_info.reddit_context.post_title
        self._update_task_status(
            status="in_progress",
            progress=100,
            stage="commission_complete",
            message=f"Commission finished: Illustrated {post_title}"
        )
    
    async def _create_zazzle_product(self, product_info: ProductInfo, donation: Donation) -> bool:
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
            
            # For commissions, we need to create a minimal pipeline run to satisfy the database constraints
            from app.db.models import PipelineRun
            from app.pipeline_status import PipelineStatus
            from app.db.mappers import reddit_context_to_db, product_info_to_db
            
            pipeline_run = PipelineRun(
                status=PipelineStatus.COMPLETED.value,  # Use the correct status value
                summary=f"Commission for donation {donation.id}",
                config={"commission": True, "donation_id": donation.id},
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=0,
                version="1.0.0"
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
                logger.error("No reddit_context found in product_info; cannot create RedditPost for commission.")
                self.db.rollback()
                return
            db_reddit_post = reddit_context_to_db(reddit_context, pipeline_run.id, self.db)
            self.db.add(db_reddit_post)
            self.db.flush()  # Get the ID without committing

            # Create the database product info with the pipeline run ID and reddit post ID
            db_product_info = product_info_to_db(product_info, pipeline_run_id=pipeline_run.id, reddit_post_id=db_reddit_post.id)
            
            # Store donation info in design_description for tracking
            donation_info = f"Commission for donation {donation.id} - {donation.customer_name}"
            if db_product_info.design_description:
                db_product_info.design_description = f"{db_product_info.design_description}\n\n{donation_info}"
            else:
                db_product_info.design_description = donation_info
            
            # Save to database
            self.db.add(db_product_info)
            self.db.commit()
            
            logger.info(f"Saved product to database with ID: {db_product_info.id} (pipeline run: {pipeline_run.id}, reddit post: {db_reddit_post.id})")
            
        except Exception as e:
            logger.error(f"Error saving product: {e}")
            self.db.rollback()
    
    def _update_donation_status(self, donation: Donation, success: bool, error: str = None):
        """Update donation status."""
        try:
            if success:
                donation.status = DonationStatus.SUCCEEDED.value
                logger.info(f"Updated donation {self.donation_id} status to SUCCEEDED")
            else:
                donation.status = DonationStatus.FAILED.value
                if error:
                    donation.message = f"Commission failed: {error}"
                logger.error(f"Updated donation {self.donation_id} status to FAILED")
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error updating donation status: {e}")
            self.db.rollback()

    async def _progress_callback(self, stage: str, data: dict):
        """Callback for RedditAgent progress updates."""
        if stage == "post_fetched":
            await self._broadcast_post_fetched(self.donation, data.get("post_title", ""))
        elif stage == "product_designed":
            # Create a mock ProductInfo for the broadcast
            class MockProductInfo:
                theme = data.get("theme", "")
            await self._broadcast_product_designed(MockProductInfo(), self.donation)


def main():
    """Main entry point for the commission worker."""
    parser = argparse.ArgumentParser(description="Commission Worker")
    parser.add_argument("--donation-id", type=int, required=True, help="Donation ID to process")
    parser.add_argument("--task-data", type=str, required=True, help="Task data as JSON string")
    
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