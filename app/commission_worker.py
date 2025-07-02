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

from app.agents.reddit_agent import RedditAgent
from app.content_generator import ContentGenerator
from app.image_generator import ImageGenerator
from app.zazzle_product_designer import ZazzleProductDesigner
from app.affiliate_linker import ZazzleAffiliateLinker
from app.clients.imgur_client import ImgurClient
from app.db.database import SessionLocal
from app.db.models import Donation, ProductInfo, PipelineTask
from app.models import DonationStatus
from app.services.commission_validator import CommissionValidator
from app.utils.logging_config import get_logger
from app.utils.openai_usage_tracker import log_session_summary
from app.websocket_manager import websocket_manager

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
    
    def _update_task_status(self, status: str, error_message: str = None):
        """Update the pipeline task status and broadcast over WebSocket."""
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
            
            # Broadcast update over WebSocket
            import asyncio
            update = {
                "status": self.pipeline_task.status,
                "completed_at": self.pipeline_task.completed_at.isoformat() if self.pipeline_task.completed_at else None,
                "error": self.pipeline_task.error_message,
            }
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(websocket_manager.broadcast_task_update(str(self.pipeline_task.id), update))
                else:
                    loop.run_until_complete(websocket_manager.broadcast_task_update(str(self.pipeline_task.id), update))
            except RuntimeError:
                # If no event loop, create one
                asyncio.run(websocket_manager.broadcast_task_update(str(self.pipeline_task.id), update))
            
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
                }
            )
            
            # Generate product
            product_info = await self.reddit_agent.find_and_create_product_for_task()
            if not product_info:
                logger.error("Failed to generate product from Reddit post")
                return None
            
            logger.info(f"Generated product: {product_info.theme}")
            return product_info
            
        except Exception as e:
            logger.error(f"Error generating product: {e}")
            return None
    
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
        import asyncio
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