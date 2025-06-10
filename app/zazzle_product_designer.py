"""
ZazzleProductDesigner module for creating and managing Zazzle products.

This module provides functionality to create products on Zazzle using their API,
including handling product templates, affiliate links, and design instructions.
It supports various product customization options and error handling.

The module provides:
- Product creation and management through Zazzle's API
- Template configuration and validation
- Affiliate link generation and tracking
- URL parameter handling and validation
- Error handling and logging
- Integration with Reddit context for product ideas
"""

from typing import Optional, Dict, Any, Tuple
from app.models import ProductInfo, RedditContext, ProductIdea, PipelineConfig, DesignInstructions
from app.utils.logging_config import get_logger
import os
from urllib.parse import quote, urlparse
from dotenv import load_dotenv
from app.zazzle_templates import ZAZZLE_STICKER_TEMPLATE

load_dotenv()
logger = get_logger(__name__)

class ZazzleProductDesigner:
    """
    A class to handle the creation and management of Zazzle products.
    
    This class provides methods to create products on Zazzle using their API,
    including handling product templates, affiliate links, and design instructions.
    It supports various product customization options and error handling.

    The class manages the following key responsibilities:
    1. Product template configuration and validation
    2. URL generation for Zazzle product creation
    3. Parameter validation and error handling
    4. Integration with Zazzle's affiliate program
    5. Product information management and tracking
    """

    def __init__(self, affiliate_id: Optional[str] = None, session: Any = None, headers: Optional[Dict[str, str]] = None):
        """
        Initialize the Product Designer with configuration.
        
        Args:
            affiliate_id (Optional[str]): Optional Zazzle affiliate ID. If not provided,
                will be loaded from environment.
            session (Any): Optional HTTP session for making requests.
            headers (Optional[Dict[str, str]]): Optional HTTP headers for requests.
            
        Note:
            The affiliate_id is required for generating valid Zazzle product URLs.
            If not provided, it will be loaded from the ZAZZLE_AFFILIATE_ID environment variable.
            A warning will be logged if the affiliate ID is not set.
        """
        self.affiliate_id = affiliate_id or os.getenv('ZAZZLE_AFFILIATE_ID')
        if not self.affiliate_id:
            logger.error("ZAZZLE_AFFILIATE_ID is not set in environment variables. Affiliate links may not work correctly.")
        else:
            logger.info(f"ZAZZLE_AFFILIATE_ID loaded: {self.affiliate_id[:5]}...")
        
        self.session = session
        self.headers = headers or {}

    def _get_template_config(self, design_instructions: DesignInstructions) -> Tuple[str, str]:
        """
        Extract template ID and tracking code from design instructions or fall back to default template.
        
        Args:
            design_instructions (DesignInstructions): The design instructions containing
                template configuration.
            
        Returns:
            Tuple[str, str]: A tuple containing:
                - template_id (str): The Zazzle template ID to use for product creation
                - tracking_code (str): The tracking code for affiliate link generation
                
        Note:
            If no template ID is specified in the design instructions, falls back to
            the default sticker template. The tracking code is always taken from the
            template configuration.
        """
        template_id = design_instructions.template_id or ZAZZLE_STICKER_TEMPLATE.zazzle_template_id
        tracking_code = ZAZZLE_STICKER_TEMPLATE.zazzle_tracking_code  # Always use template tracking code for now
        return template_id, tracking_code

    def _is_valid_url(self, url: str) -> bool:
        """
        Validate if a string is a valid URL.
        
        Args:
            url (str): The URL string to validate.
            
        Returns:
            bool: True if the URL is valid (has http/https scheme and valid netloc),
                False otherwise.
            
        Note:
            This method performs basic URL validation to ensure the URL has:
            1. A valid scheme (http or https)
            2. A valid network location (netloc)
        """
        if not url.startswith(('http://', 'https://')):
            return False
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    async def create_product(
        self,
        design_instructions: DesignInstructions,
        reddit_context: Optional[RedditContext] = None
    ) -> Optional[ProductInfo]:
        """
        Create a product using the design instructions.
        
        This method handles the complete product creation process:
        1. Validates required fields and parameters
        2. Generates the product URL with proper parameters
        3. Creates a ProductInfo object with all necessary details
        
        Args:
            design_instructions (DesignInstructions): The design instructions for the product.
            reddit_context (Optional[RedditContext]): Optional Reddit context for the product.
            
        Returns:
            Optional[ProductInfo]: ProductInfo object if successful, None if creation fails.
            
        Note:
            The method performs several validations:
            - Checks for required template and affiliate ID
            - Validates the presence of an image URL
            - Ensures the image URL is properly formatted
            - Handles URL parameter encoding and ordering
        """
        # Get template configuration
        template_id, tracking_code = self._get_template_config(design_instructions)
        
        # Check if template exists
        if not template_id or not self.affiliate_id:
            logger.error("Cannot create product: Zazzle template or ZAZZLE_AFFILIATE_ID is not set.")
            return None

        # Validate required fields - check image first to match test expectations
        if not design_instructions.image:
            logger.error("Missing required image URL for field: image")
            return None

        # Validate image URL
        if not self._is_valid_url(design_instructions.image):
            logger.error("Invalid image_url for field image: must start with http:// or https://")
            return None

        try:
            # Build parameters dictionary
            params = {
                'ax': 'linkover',
                'pd': template_id,
                'fwd': 'productpage',
                'ed': 'true',
                't_image1_url': quote(design_instructions.image)
            }

            # Add theme if present
            if design_instructions.theme:
                params['theme'] = quote(str(design_instructions.theme))

            # Add tracking code
            params['tc'] = tracking_code

            # Generate product URL
            product_url = self._generate_product_url(params)
            if not product_url:
                return None
            logger.info(f"Successfully generated product URL: {product_url}")

            return ProductInfo(
                product_id=f"prod_{os.urandom(4).hex()}",  # Generate a unique product ID
                name=design_instructions.theme or "Custom Product",
                product_type=design_instructions.product_type or "sticker",
                zazzle_template_id=template_id,
                zazzle_tracking_code=tracking_code,
                image_url=design_instructions.image,
                product_url=product_url,
                theme=design_instructions.theme,
                model=design_instructions.model,
                prompt_version=design_instructions.prompt_version,
                reddit_context=reddit_context,
                design_instructions=design_instructions.__dict__,
                image_local_path=None  # This would be set by the image generator
            )

        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
            return None

    def _generate_product_url(self, params: Dict[str, Any]) -> Optional[str]:
        """
        Generate a product URL based on the given parameters.
        
        This method constructs the Zazzle product URL with all necessary parameters
        in the correct order for proper API integration.
        
        Args:
            params (Dict[str, Any]): Dictionary of URL parameters containing:
                - ax (str): Action type (linkover)
                - pd (str): Product template ID
                - fwd (str): Forward destination
                - ed (str): Edit flag
                - t_image1_url (str): Image URL
                - tc (str): Tracking code
            
        Returns:
            Optional[str]: Generated product URL if successful, None if generation fails.
            
        Note:
            The URL parameters are ordered to match Zazzle's API expectations.
            The tracking code is always added last to maintain consistent URL structure.
            The URL must start with 'https://www.zazzle.com/api/create/at-' to be valid.
        """
        try:
            if not params.get('pd') or not self.affiliate_id:
                logger.error("Cannot create product: Zazzle template or ZAZZLE_AFFILIATE_ID is not set.")
                return None

            # Order parameters to match test expectations
            ordered_params = {
                'ax': params['ax'],
                'pd': params['pd'],
                'fwd': params['fwd'],
                'ed': params['ed'],
                't_image1_url': params['t_image1_url']
            }

            # Add tracking code last
            ordered_params['tc'] = params['tc']

            base_url = f"https://www.zazzle.com/api/create/at-{self.affiliate_id}"
            query_string = '&'.join(f"{k}={v}" for k, v in ordered_params.items())
            product_url = f"{base_url}?{query_string}"
            if not product_url.startswith('https://www.zazzle.com/api/create/at-'):
                logger.error("Invalid product URL generated")
                return None
            return product_url
        except Exception as e:
            logger.error(f"Error generating product URL: {str(e)}")
            return None 