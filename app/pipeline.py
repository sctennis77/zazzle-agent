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

from typing import List, Optional, Dict, Any
import asyncio
from datetime import datetime
from app.models import ProductIdea, ProductInfo, PipelineConfig, RedditContext, DesignInstructions
from app.agents.reddit_agent import RedditAgent
from app.content_generator import ContentGenerator
from app.image_generator import ImageGenerator
from app.zazzle_product_designer import ZazzleProductDesigner
from app.affiliate_linker import ZazzleAffiliateLinker
from app.clients.imgur_client import ImgurClient
from app.utils.logging_config import get_logger
from app.zazzle_templates import ZAZZLE_STICKER_TEMPLATE
from app.db.mappers import product_idea_to_db, product_info_to_db
from app.db.models import PipelineRun, ErrorLog
from sqlalchemy.orm import Session

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
        pipeline_run_id: int = None,
        session = None,
        reddit_post_id: int = None
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
            zazzle_template_id=ZAZZLE_STICKER_TEMPLATE.zazzle_template_id,
            zazzle_tracking_code=ZAZZLE_STICKER_TEMPLATE.zazzle_tracking_code,
            prompt_version="1.0.0"
        )
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.pipeline_run_id = pipeline_run_id
        self.session = session
        self.reddit_post_id = reddit_post_id

    def log_error(self, error_message: str):
        """Log an error to the database if session is available."""
        if self.session and self.pipeline_run_id:
            error_log = ErrorLog(
                pipeline_run_id=self.pipeline_run_id,
                error_message=error_message
            )
            self.session.add(error_log)
            self.session.commit()
            logger.error(f"Logged error to database: {error_message}")

    async def process_product_idea(self, product_idea: ProductIdea) -> Optional[ProductInfo]:
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
                template_id=product_idea.design_instructions.get("template_id")
            )
            product_idea.design_instructions["image"] = imgur_url

            # Persist ProductIdea as ProductInfo in the DB if session and pipeline_run_id are provided
            product_info_db_id = None
            if self.session and self.pipeline_run_id and self.reddit_post_id:
                orm_product = product_idea_to_db(product_idea, self.pipeline_run_id, self.reddit_post_id)
                self.session.add(orm_product)
                self.session.commit()
                product_info_db_id = orm_product.id
                logger.info(f"Persisted ProductInfo with id {product_info_db_id}")

            # Create product with retries
            for attempt in range(self.max_retries):
                try:
                    product_info = await self.zazzle_designer.create_product(
                        design_instructions=product_idea.design_instructions,
                        reddit_context=product_idea.reddit_context
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
            products_with_links = await self.affiliate_linker.generate_links_batch([product_info])
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

    async def run(self, pipeline_run_id: int, session: Session) -> List[ProductInfo]:
        """
        Run the pipeline to generate products from Reddit content.
        Updates pipeline run status in the database.
        """
        try:
            # Update pipeline run status to 'running'
            if session:
                pipeline_run = session.query(PipelineRun).get(pipeline_run_id)
                if pipeline_run:
                    pipeline_run.status = 'running'
                    session.commit()

            # Use the injected RedditAgent (self.reddit_agent) instead of creating a new one
            self.reddit_agent.session = session
            self.reddit_agent.pipeline_run_id = pipeline_run_id
            # Find a trending post and create a product
            product_info = await self.reddit_agent.find_and_create_product()
            if product_info:
                # Persist RedditContext to get reddit_post_id
                reddit_post_id = self.reddit_agent.save_reddit_context_to_db(product_info.reddit_context)
                # Persist ProductInfo with the reddit_post_id
                orm_product = product_info_to_db(product_info, pipeline_run_id, reddit_post_id)
                session.add(orm_product)
                session.commit()
                logger.info(f"Persisted ProductInfo with id {orm_product.id}")

                # Update pipeline run status to 'success'
                if session:
                    pipeline_run = session.query(PipelineRun).get(pipeline_run_id)
                    if pipeline_run:
                        pipeline_run.status = 'success'
                        pipeline_run.end_time = datetime.utcnow()
                        session.commit()

                return [product_info]

            # Update pipeline run status to 'no_products'
            if session:
                pipeline_run = session.query(PipelineRun).get(pipeline_run_id)
                if pipeline_run:
                    pipeline_run.status = 'no_products'
                    pipeline_run.end_time = datetime.utcnow()
                    session.commit()

            return []
        except Exception as e:
            error_msg = f"Error in pipeline run: {str(e)}"
            self.log_error(error_msg)
            logger.error(error_msg)

            # Update pipeline run status to 'error'
            if session:
                pipeline_run = session.query(PipelineRun).get(pipeline_run_id)
                if pipeline_run:
                    pipeline_run.status = 'error'
                    pipeline_run.end_time = datetime.utcnow()
                    session.commit()

            raise  # Re-raise the exception

    async def run_pipeline(self) -> List[ProductInfo]:
        """
        Run the full pipeline to generate products from Reddit content.
        
        Returns:
            List[ProductInfo]: List of successfully generated products
        """
        try:
            # Get product info from Reddit
            products = await self.reddit_agent.get_product_info()
            if not products:
                logger.warning("No products were generated")
                return []

            # Generate affiliate links for all products
            products_with_links = await self.affiliate_linker.generate_links_batch(products)
            if not products_with_links:
                error_msg = "No products were successfully processed with affiliate links"
                self.log_error(error_msg)
                logger.warning(error_msg)
                raise Exception(error_msg)

            return products_with_links
        except Exception as e:
            error_msg = f"Error in run_pipeline: {str(e)}"
            self.log_error(error_msg)
            logger.error(error_msg)
            raise  # Re-raise the exception 