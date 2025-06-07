import os
import logging
from typing import Dict, Optional
from urllib.parse import quote
from dotenv import load_dotenv
import re

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ZazzleProductDesigner:
    """Agent responsible for generating custom products on Zazzle using the Create-a-Product system."""

    def __init__(self):
        """Initialize the Product Designer with configuration."""
        self.affiliate_id = os.getenv('ZAZZLE_AFFILIATE_ID')
        if not self.affiliate_id:
            logger.error("ZAZZLE_AFFILIATE_ID is not set in environment variables. Affiliate links may not work correctly.")
        else:
            logger.info(f"ZAZZLE_AFFILIATE_ID loaded: {self.affiliate_id[:5]}...")
        # Load template ID from environment variable
        self.template_id = os.getenv('ZAZZLE_TEMPLATE_ID')
        if not self.template_id:
            logger.error("ZAZZLE_TEMPLATE_ID is not set in environment variables. Product creation may fail.")
        else:
            logger.info(f"ZAZZLE_TEMPLATE_ID loaded: {self.template_id}")
        
        self.tracking_code = os.getenv('ZAZZLE_TRACKING_CODE', '') # Load tracking code

    def create_product(self, product_info: Dict) -> Optional[Dict]:
        """Create a custom sticker product using Zazzle's Create-a-Product system."""
        try:
            if not self.template_id or not self.affiliate_id:
                logger.error("Cannot create product: ZAZZLE_TEMPLATE_ID or ZAZZLE_AFFILIATE_ID is not set.")
                return None

            # Validate required fields
            required_fields = ['text', 'image_url', 'image_iid', 'theme']
            for field in required_fields:
                if not product_info.get(field):
                    logger.error(f"Missing required field: {field}")
                    return None

            # Validate image_url (basic check)
            image_url = product_info.get('image_url', '')
            if not (image_url.startswith('http://') or image_url.startswith('https://')):
                logger.error("Invalid image_url: must start with http:// or https://")
                return None

            # Construct the deep link URL with product details
            base_url = f"https://www.zazzle.com/api/create/at-{self.affiliate_id}"
            params = {
                'ax': 'linkover',
                'pd': self.template_id,
                'fwd': 'productpage',
                'ed': 'true', # Allow customization
                't_text1_txt': product_info['text'],
                't_image1_iid': product_info['image_iid']
            }
            # Add color and quantity if present
            if product_info.get('color'):
                params['color'] = product_info['color']
            if product_info.get('quantity'):
                params['quantity'] = product_info['quantity']
            # Add tracking code if available
            if self.tracking_code:
                params['tc'] = self.tracking_code
            # Construct the final URL
            query_string = '&'.join(f"{k}={quote(str(v))}" for k, v in params.items())
            product_url = f"{base_url}?{query_string}"
            # Validate the URL
            if not product_url.startswith('https://www.zazzle.com/api/create/at-'):
                logger.error("Invalid product URL generated")
                return None
            logger.info(f"Successfully generated product URL: {product_url}")
            # Return the product info with the CAP URL
            return {
                'product_url': product_url,
                'text': product_info['text'],
                'image_url': product_info['image_url'],
                'theme': product_info['theme']
            }
        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
            return None

if __name__ == '__main__':
    # Example usage
    # Make sure ZAZZLE_AFFILIATE_ID and ZAZZLE_TEMPLATE_ID are set in .env
    designer = ZazzleProductDesigner()
    design_instructions = {
        'text': 'FIRE THE CANNONS!',
        'image_url': 'https://via.placeholder.com/150', # This will be ignored for pre-population, need IID
        'image_iid': 'test_image_iid',
        'theme': 'test_theme',
        'color': 'Blue',
        'quantity': 12
    }
    result = designer.create_product(design_instructions)
    print(result) 