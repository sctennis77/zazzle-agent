"""
Task Runner service for processing pipeline tasks from the queue.

This module provides an async task processor that runs periodically to execute
tasks from the pipeline task queue.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.affiliate_linker import ZazzleAffiliateLinker
from app.agents.reddit_agent import RedditAgent
from app.clients.imgur_client import ImgurClient
from app.content_generator import ContentGenerator
from app.db.database import SessionLocal
from app.db.models import PipelineTask
from app.image_generator import ImageGenerator
from app.models import PipelineConfig
from app.pipeline import Pipeline
from app.task_queue import TaskQueue
from app.utils.logging_config import get_logger
from app.zazzle_product_designer import ZazzleProductDesigner
from app.zazzle_templates import ZAZZLE_PRINT_TEMPLATE

logger = get_logger(__name__)


class TaskRunner:
    """Service for processing tasks from the pipeline queue."""

    def __init__(self, processing_interval: int = 300):  # 5 minutes default
        """
        Initialize the task runner.
        
        Args:
            processing_interval: Interval between task processing runs in seconds
        """
        self.processing_interval = processing_interval
        self.running = False
        self.session: Optional[Session] = None

    async def start(self):
        """Start the task runner service."""
        logger.info("Starting Task Runner service...")
        self.running = True
        
        while self.running:
            try:
                await self.process_tasks()
                await asyncio.sleep(self.processing_interval)
            except Exception as e:
                logger.error(f"Error in task runner loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    def stop(self):
        """Stop the task runner service."""
        logger.info("Stopping Task Runner service...")
        self.running = False

    async def process_tasks(self):
        """Process tasks from the queue."""
        try:
            session = SessionLocal()
            task_queue = TaskQueue(session)
            
            # Get the next task
            task = task_queue.get_next_task()
            if not task:
                logger.debug("No tasks available for processing")
                return
            
            logger.info(f"Processing task {task.id} (type: {task.type})")
            
            # Process the task
            success = await self._process_single_task(task, session)
            
            if success:
                logger.info(f"Successfully processed task {task.id}")
            else:
                logger.error(f"Failed to process task {task.id}")
                
        except Exception as e:
            logger.error(f"Error processing tasks: {str(e)}")
        finally:
            if 'session' in locals():
                session.close()

    async def _process_single_task(self, task: PipelineTask, session: Session) -> bool:
        """
        Process a single task.
        
        Args:
            task: The task to process
            session: Database session
            
        Returns:
            bool: True if task was processed successfully, False otherwise
        """
        try:
            # Mark task as in progress
            task_queue = TaskQueue(session)
            task_queue.mark_in_progress(task.id)
            
            # Initialize pipeline components
            config = PipelineConfig(
                model="dall-e-3",
                zazzle_template_id=ZAZZLE_PRINT_TEMPLATE.zazzle_template_id,
                zazzle_tracking_code=ZAZZLE_PRINT_TEMPLATE.zazzle_tracking_code,
                zazzle_affiliate_id=os.getenv("ZAZZLE_AFFILIATE_ID", ""),
                prompt_version="1.0.0",
            )
            
            reddit_agent = RedditAgent(
                config,
                pipeline_run_id=None,  # Will be set by pipeline
                session=session,
                subreddit_name=task.subreddit,
            )
            
            content_generator = ContentGenerator()
            image_generator = ImageGenerator(model=config.model)
            zazzle_designer = ZazzleProductDesigner()
            affiliate_linker = ZazzleAffiliateLinker(
                zazzle_affiliate_id=os.getenv("ZAZZLE_AFFILIATE_ID", ""),
                zazzle_tracking_code=os.getenv("ZAZZLE_TRACKING_CODE", ""),
            )
            imgur_client = ImgurClient()
            
            # Create pipeline
            pipeline = Pipeline(
                reddit_agent=reddit_agent,
                content_generator=content_generator,
                image_generator=image_generator,
                zazzle_designer=zazzle_designer,
                affiliate_linker=affiliate_linker,
                imgur_client=imgur_client,
                config=config,
                session=session,
            )
            
            # Run the task pipeline
            products = await pipeline.run_task_pipeline(task.id)
            
            if products:
                logger.info(f"Task {task.id} completed successfully, generated {len(products)} products")
                return True
            else:
                logger.error(f"Task {task.id} failed to generate products")
                return False
                
        except Exception as e:
            error_msg = f"Error processing task {task.id}: {str(e)}"
            logger.error(error_msg)
            
            # Mark task as failed
            task_queue = TaskQueue(session)
            task_queue.mark_completed(task.id, error_message=error_msg)
            
            return False

    async def run_once(self) -> bool:
        """
        Run task processing once (for testing or manual execution).
        
        Returns:
            bool: True if tasks were processed, False otherwise
        """
        try:
            await self.process_tasks()
            return True
        except Exception as e:
            logger.error(f"Error in run_once: {str(e)}")
            return False


async def main():
    """Main function to run the task runner."""
    runner = TaskRunner()
    
    try:
        await runner.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, stopping task runner...")
        runner.stop()
    except Exception as e:
        logger.error(f"Unexpected error in task runner: {str(e)}")
        runner.stop()


if __name__ == "__main__":
    asyncio.run(main()) 