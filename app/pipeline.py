"""
Pipeline module for the Zazzle Agent application.

This module provides the main pipeline for processing product ideas into product info objects.
It orchestrates the entire product generation process from Reddit content to final product.

The module handles:
- Product idea generation from Reddit
- Content generation
- Image generation
- Product creation
- Affiliate link generation
- Pipeline configuration management
- Database persistence and error logging
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.affiliate_linker import ZazzleAffiliateLinker
from app.agents.reddit_agent import RedditAgent
from app.clients.imgur_client import ImgurClient
from app.content_generator import ContentGenerator
from app.db.database import SessionLocal
from app.db.mappers import product_idea_to_db, product_info_to_db, reddit_context_to_db
from app.db.models import ErrorLog, PipelineRun, PipelineRunUsage, PipelineTask
from app.image_generator import ImageGenerator
from app.models import (
    DesignInstructions,
    PipelineConfig,
    ProductIdea,
    ProductInfo,
    RedditContext,
)
from app.pipeline_status import PipelineStatus
from app.task_queue import TaskQueue
from app.utils.logging_config import get_logger
from app.zazzle_product_designer import ZazzleProductDesigner
from app.zazzle_templates import ZAZZLE_PRINT_TEMPLATE
from app.utils.openai_usage_tracker import get_usage_tracker
from decimal import Decimal

logger = get_logger(__name__)

class Pipeline:
    """
    Main pipeline for processing product ideas into product info objects.

    This class orchestrates the complete product generation process:
    1. Product idea generation from Reddit
    2. Content generation
    3. Image generation
    4. Product creation
    5. Affiliate link generation

    The class supports:
    - Single product idea processing
    - Batch processing of multiple ideas
    - Configurable pipeline settings
    - Dependency injection for testing
    - Database persistence and error logging
    """

    def __init__(
        self,
        reddit_agent: RedditAgent,
        content_generator: ContentGenerator,
        image_generator: ImageGenerator,
        zazzle_designer: ZazzleProductDesigner,
        affiliate_linker: ZazzleAffiliateLinker,
        imgur_client: ImgurClient,
        config: Optional[PipelineConfig] = None,
        pipeline_run_id: Optional[int] = None,
        session: Optional[Session] = None,
        reddit_post_id: Optional[int] = None,
    ):
        """
        Initialize the pipeline with its dependencies.
        Optionally accepts pipeline_run_id, session, and reddit_post_id for DB persistence.

        Args:
            reddit_agent: Agent for Reddit interaction and product idea generation
            content_generator: Generator for product content
            image_generator: Generator for product images
            zazzle_designer: Designer for Zazzle products
            affiliate_linker: Generator for affiliate links
            imgur_client: Client for image uploads
            config: Optional pipeline configuration
            pipeline_run_id: ID of the current pipeline run
            session: SQLAlchemy session for DB operations
            reddit_post_id: ID of the current Reddit post
        """
        self.reddit_agent = reddit_agent
        self.content_generator = content_generator
        self.image_generator = image_generator
        self.zazzle_designer = zazzle_designer
        self.affiliate_linker = affiliate_linker
        self.imgur_client = imgur_client
        self.config = config or PipelineConfig(
            model="dall-e-3",
            zazzle_template_id=ZAZZLE_PRINT_TEMPLATE.zazzle_template_id,
            zazzle_tracking_code=ZAZZLE_PRINT_TEMPLATE.zazzle_tracking_code,
            zazzle_affiliate_id=os.getenv("ZAZZLE_AFFILIATE_ID", ""),
            prompt_version="1.0.0",
        )
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.pipeline_run_id = pipeline_run_id
        self.session = session
        self.reddit_post_id = reddit_post_id

    def log_error(
        self,
        error_message: str,
        error_type: str = "SYSTEM_ERROR",
        component: str = "PIPELINE",
        stack_trace: Optional[str] = None,
        context_data: Optional[dict] = None,
        severity: str = "ERROR",
    ) -> None:
        """
        Log an error to the database if session is available.

        Args:
            error_message: The error message to log
            error_type: Type of error (e.g., 'API_ERROR', 'VALIDATION_ERROR', 'SYSTEM_ERROR')
            component: Component where error occurred (e.g., 'REDDIT_AGENT', 'IMAGE_GENERATOR')
            stack_trace: Full stack trace if available
            context_data: Additional context data as dictionary
            severity: Error severity ('ERROR', 'WARNING', 'INFO')
        """
        if self.session and self.pipeline_run_id:
            try:
                error_log = ErrorLog(
                    pipeline_run_id=self.pipeline_run_id,
                    error_message=error_message,
                    error_type=error_type,
                    component=component,
                    stack_trace=stack_trace,
                    context_data=context_data,
                    severity=severity,
                    timestamp=datetime.utcnow(),
                )
                self.session.add(error_log)

                # Update pipeline run with last error
                pipeline_run = self.session.query(PipelineRun).get(self.pipeline_run_id)
                if pipeline_run:
                    pipeline_run.last_error = error_message
                    pipeline_run.status = PipelineStatus.FAILED.value
                    pipeline_run.end_time = datetime.utcnow()
                    if pipeline_run.start_time:
                        pipeline_run.duration = int(
                            (
                                pipeline_run.end_time - pipeline_run.start_time
                            ).total_seconds()
                        )
                self.session.commit()
                logger.error(
                    f"Logged error to database: {error_message} "
                    f"(Type: {error_type}, Component: {component})"
                )
            except Exception as e:
                logger.error(f"Failed to log error to database: {str(e)}")
                self.session.rollback()
                raise

    async def process_product_idea(
        self, product_idea: ProductIdea
    ) -> Optional[ProductInfo]:
        """
        Process a single product idea through the pipeline.
        Persists ProductIdea as ProductInfo in the DB if session and pipeline_run_id are provided.

        Args:
            product_idea: ProductIdea object to process

        Returns:
            Optional[ProductInfo]: Processed ProductInfo object if successful, None if failed
        """
        try:
            # Generate content
            content = await self.content_generator.generate_content(product_idea.theme)
            product_idea.design_instructions["content"] = content

            # Generate image
            imgur_url, local_path = await self.image_generator.generate_image(
                product_idea.image_description,
                template_id=product_idea.design_instructions.get("template_id"),
            )
            product_idea.design_instructions["image"] = imgur_url

            # Create product with retries
            product_info: Optional[ProductInfo] = None
            for attempt in range(self.max_retries):
                try:
                    product_info = await self.zazzle_designer.create_product(
                        design_instructions=product_idea.design_instructions,
                        reddit_context=product_idea.reddit_context,
                    )
                    if product_info:
                        break
                except Exception as e:
                    error_msg = f"Failed to create product (attempt {attempt + 1}/{self.max_retries}): {str(e)}"
                    self.log_error(error_msg)
                    if attempt == self.max_retries - 1:
                        logger.error(error_msg)
                        raise  # Re-raise the exception after all retries
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

            if not product_info:
                error_msg = "Failed to create product after all retries"
                self.log_error(error_msg)
                logger.error(error_msg)
                raise Exception(error_msg)

            # Generate affiliate link
            products_with_links = await self.affiliate_linker.generate_links_batch(
                [product_info]
            )
            if not products_with_links:
                error_msg = "Failed to generate affiliate links"
                self.log_error(error_msg)
                logger.error(error_msg)
                raise Exception(error_msg)

            return products_with_links[0]

        except Exception as e:
            error_msg = f"Error processing product idea: {str(e)}"
            self.log_error(error_msg)
            logger.error(error_msg)
            raise  # Re-raise the exception

    async def run_pipeline(self) -> List[ProductInfo]:
        """
        Run the full pipeline to generate products from Reddit content.

        Returns:
            List[ProductInfo]: List of successfully generated products
        """
        try:
            # Use the session from the test environment if provided
            session = self.session or SessionLocal()

            # Use existing pipeline run if available
            if self.pipeline_run_id:
                pipeline_run = session.query(PipelineRun).get(self.pipeline_run_id)
                if not pipeline_run:
                    raise ValueError(f"Pipeline run {self.pipeline_run_id} not found")
            else:
                # Create a new pipeline run
                pipeline_run = PipelineRun(
                    status=PipelineStatus.STARTED.value, start_time=datetime.utcnow()
                )
                session.add(pipeline_run)
                session.commit()
                self.pipeline_run_id = pipeline_run.id

            # Get product info from Reddit
            products = await self.reddit_agent.get_product_info()
            if not products:
                error_msg = (
                    f"No products were generated. pipeline_run_id: {pipeline_run.id}"
                )
                raise Exception(error_msg)

            # Convert single product to list for consistency
            if not isinstance(products, list):
                products = [products]

            # Generate affiliate links for all products
            products_with_links = await self.affiliate_linker.generate_links_batch(
                products
            )
            if not products_with_links:
                error_msg = f"No products were successfully processed with affiliate links pipeline_run_id: {pipeline_run.id}"
                raise Exception(error_msg)

            orm_reddit_post = None
            if products:
                reddit_context = products[0].reddit_context
                orm_reddit_post = reddit_context_to_db(reddit_context, pipeline_run.id)
                session.add(orm_reddit_post)
                session.commit()
                self.reddit_post_id = orm_reddit_post.id
                logger.info(f"Persisted RedditPost with id {self.reddit_post_id}")

            # Persist only the first ProductInfo to DB using ORM
            if products_with_links and orm_reddit_post:
                product_info = products_with_links[0]
                orm_product_info = product_info_to_db(
                    product_info, pipeline_run.id, self.reddit_post_id
                )
                orm_product_info.reddit_post_id = orm_reddit_post.id
                session.add(orm_product_info)
                session.commit()
                logging.debug(
                    f"Persisted ProductInfo with ID: {orm_product_info.id} and RedditPost ID: {orm_reddit_post.id}"
                )

            # Update pipeline run status
            pipeline_run.status = PipelineStatus.COMPLETED.value
            pipeline_run.end_time = datetime.utcnow()
            
            # Track OpenAI usage for this pipeline run
            try:
                usage_tracker = get_usage_tracker()
                usage_summary = usage_tracker.get_session_summary()
                
                # Extract usage data
                total_tokens = usage_summary.get("total_tokens_used", 0)
                total_cost = usage_summary.get("total_cost_usd", "$0.0000")
                model_breakdown = usage_summary.get("model_breakdown", {})
                
                # Determine models used
                idea_model = "gpt-3.5-turbo"  # Default
                image_model = self.config.model if self.config else "dall-e-3"
                
                # Find the actual models used from the breakdown
                for model, data in model_breakdown.items():
                    if data.get("calls", 0) > 0:
                        if "gpt" in model.lower():
                            idea_model = model
                        elif "dall" in model.lower():
                            image_model = model
                
                # Calculate token breakdown (approximate)
                prompt_tokens = int(total_tokens * 0.8)  # Assume 80% prompt, 20% completion
                completion_tokens = total_tokens - prompt_tokens
                image_tokens = 0  # DALL-E doesn't use tokens in the same way
                
                # Parse cost string to decimal
                cost_str = total_cost.replace("$", "")
                total_cost_decimal = Decimal(cost_str)
                
                # Create usage record
                pipeline_usage = PipelineRunUsage(
                    pipeline_run_id=pipeline_run.id,
                    idea_model=idea_model,
                    image_model=image_model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    image_tokens=image_tokens,
                    total_cost_usd=total_cost_decimal
                )
                session.add(pipeline_usage)
                
                logger.info(f"Tracked OpenAI usage for pipeline run {pipeline_run.id}: "
                          f"idea_model={idea_model}, image_model={image_model}, "
                          f"tokens={total_tokens}, cost={total_cost}")
                
            except Exception as e:
                logger.warning(f"Failed to track OpenAI usage for pipeline run {pipeline_run.id}: {str(e)}")
            
            session.commit()

            # Check if pipeline run exists
            if not session.query(PipelineRun).get(pipeline_run.id):
                raise ValueError(f"Pipeline run {pipeline_run.id} not found")

            return products_with_links
        except Exception as e:
            error_msg = f"Error in run_pipeline with pipeline_run_id: {pipeline_run.id} and reddit_post_id: {self.reddit_post_id}: {str(e)}"
            self.log_error(error_msg)
            logger.error(error_msg)
            pipeline_run.status = PipelineStatus.FAILED.value
            pipeline_run.end_time = datetime.utcnow()
            
            # Track OpenAI usage even for failed runs
            try:
                usage_tracker = get_usage_tracker()
                usage_summary = usage_tracker.get_session_summary()
                
                # Extract usage data
                total_tokens = usage_summary.get("total_tokens_used", 0)
                total_cost = usage_summary.get("total_cost_usd", "$0.0000")
                model_breakdown = usage_summary.get("model_breakdown", {})
                
                # Determine models used
                idea_model = "gpt-3.5-turbo"  # Default
                image_model = self.config.model if self.config else "dall-e-3"
                
                # Find the actual models used from the breakdown
                for model, data in model_breakdown.items():
                    if data.get("calls", 0) > 0:
                        if "gpt" in model.lower():
                            idea_model = model
                        elif "dall" in model.lower():
                            image_model = model
                
                # Calculate token breakdown (approximate)
                prompt_tokens = int(total_tokens * 0.8)  # Assume 80% prompt, 20% completion
                completion_tokens = total_tokens - prompt_tokens
                image_tokens = 0  # DALL-E doesn't use tokens in the same way
                
                # Parse cost string to decimal
                cost_str = total_cost.replace("$", "")
                total_cost_decimal = Decimal(cost_str)
                
                # Create usage record
                pipeline_usage = PipelineRunUsage(
                    pipeline_run_id=pipeline_run.id,
                    idea_model=idea_model,
                    image_model=image_model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    image_tokens=image_tokens,
                    total_cost_usd=total_cost_decimal
                )
                session.add(pipeline_usage)
                
                logger.info(f"Tracked OpenAI usage for failed pipeline run {pipeline_run.id}: "
                          f"idea_model={idea_model}, image_model={image_model}, "
                          f"tokens={total_tokens}, cost={total_cost}")
                
            except Exception as usage_error:
                logger.warning(f"Failed to track OpenAI usage for failed pipeline run {pipeline_run.id}: {str(usage_error)}")
            
            session.commit()
            raise  # Re-raise the exception
        finally:
            logging.debug("Closing session...")
            session.close()

    async def run_task_pipeline(self, task_id: int) -> Optional[List[ProductInfo]]:
        """
        Run the pipeline for a specific task from the queue.
        
        Args:
            task_id: ID of the task to execute
            
        Returns:
            Optional[List[ProductInfo]]: List of generated products or None if failed
        """
        try:
            session = self.session or SessionLocal()
            task_queue = TaskQueue(session)
            
            # Get the task
            task = session.query(PipelineTask).get(task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return None
            
            # Mark task as in progress
            task_queue.mark_in_progress(task_id)
            
            # Create a new pipeline run for this task
            pipeline_run = PipelineRun(
                status=PipelineStatus.STARTED.value,
                start_time=datetime.utcnow(),
                config={"task_id": task_id, "task_type": task.type}
            )
            session.add(pipeline_run)
            session.commit()
            self.pipeline_run_id = pipeline_run.id
            
            logger.info(f"Starting task pipeline for task {task_id} (type: {task.type})")
            
            # Configure Reddit agent based on task type
            if task.type == "SPONSORED_POST" and task.subreddit:
                # Use specific subreddit for sponsored posts
                self.reddit_agent.subreddit_name = task.subreddit
                logger.info(f"Using subreddit {task.subreddit} for sponsored post")
            elif task.type == "FRONT_PICK":
                # Use front page for front picks
                self.reddit_agent.subreddit_name = None  # Will pick random from front
                logger.info("Using front page for front pick")
            elif task.type == "SUBREDDIT_TIER_POST" and task.subreddit:
                # Use specific subreddit for tier posts
                self.reddit_agent.subreddit_name = task.subreddit
                logger.info(f"Using subreddit {task.subreddit} for tier post")
            else:
                # Default to random subreddit
                self.reddit_agent.subreddit_name = None
                logger.info("Using random subreddit")
            
            # Run the pipeline
            products = await self.run_pipeline()
            
            # Mark task as completed
            task_queue.mark_completed(task_id)
            
            logger.info(f"Successfully completed task {task_id}, generated {len(products)} products")
            return products
            
        except Exception as e:
            error_msg = f"Error in task pipeline for task {task_id}: {str(e)}"
            logger.error(error_msg)
            
            # Mark task as failed
            if 'task_queue' in locals():
                task_queue.mark_completed(task_id, error_message=error_msg)
            
            # Log error to database
            self.log_error(error_msg, error_type="TASK_PIPELINE_ERROR", component="PIPELINE")
            
            return None
        finally:
            if 'session' in locals() and not self.session:
                session.close()

    def check_task_queue_first(self) -> Optional[int]:
        """
        Check if there are any tasks in the queue that should be processed first.
        
        Returns:
            Optional[int]: Task ID to process, or None if no tasks available
        """
        try:
            session = self.session or SessionLocal()
            task_queue = TaskQueue(session)
            
            # Get the next task
            task = task_queue.get_next_task()
            if task:
                logger.info(f"Found task {task.id} in queue, will process this instead of random content")
                return task.id
            else:
                logger.debug("No tasks in queue, will use random content")
                return None
                
        except Exception as e:
            logger.error(f"Error checking task queue: {str(e)}")
            return None
        finally:
            if 'session' in locals() and not self.session:
                session.close()
