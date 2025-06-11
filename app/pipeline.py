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
"""

from typing import List, Optional, Dict, Any
import asyncio
from app.models import ProductIdea, ProductInfo, PipelineConfig, RedditContext, DesignInstructions
from app.agents.reddit_agent import RedditAgent
from app.content_generator import ContentGenerator
from app.image_generator import ImageGenerator
from app.zazzle_product_designer import ZazzleProductDesigner
from app.affiliate_linker import ZazzleAffiliateLinker
from app.clients.imgur_client import ImgurClient
from app.utils.logging_config import get_logger
from app.zazzle_templates import ZAZZLE_STICKER_TEMPLATE

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
    """
    
    def __init__(
        self,
        reddit_agent: RedditAgent,
        content_generator: ContentGenerator,
        image_generator: ImageGenerator,
        zazzle_designer: ZazzleProductDesigner,
        affiliate_linker: ZazzleAffiliateLinker,
        imgur_client: ImgurClient,
        config: Optional[PipelineConfig] = None
    ):
        """
        Initialize the pipeline with its dependencies.
        
        Args:
            reddit_agent: Agent for Reddit interaction and product idea generation
            content_generator: Generator for product content
            image_generator: Generator for product images
            zazzle_designer: Designer for Zazzle products
            affiliate_linker: Generator for affiliate links
            imgur_client: Client for image uploads
            config: Optional pipeline configuration
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

    async def process_product_idea(self, product_idea: ProductIdea) -> Optional[ProductInfo]:
        """
        Process a single product idea through the pipeline.
        
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
                    if attempt == self.max_retries - 1:
                        logger.error(f"Failed to create product after {self.max_retries} attempts: {str(e)}")
                        return None
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

            if not product_info:
                logger.error("Failed to create product")
                return None

            # Generate affiliate link
            products_with_links = await self.affiliate_linker.generate_links_batch([product_info])
            return products_with_links[0] if products_with_links else None

        except Exception as e:
            logger.error(f"Error processing product idea: {str(e)}")
            return None

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
                logger.warning("No products were successfully processed with affiliate links")
                return []

            return products_with_links

        except Exception as e:
            logger.error(f"Error in pipeline: {str(e)}")
            raise  # Re-raise the exception for proper error handling in tests 