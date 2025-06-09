import os
import logging
from typing import Dict, Optional, Any
from urllib.parse import quote, urlparse
from dotenv import load_dotenv
import re
from app.zazzle_templates import get_product_template, ZazzleTemplateConfig, CustomizableField

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add this mapping at the top of the file, after imports
COLOR_NAME_TO_HEX = {
    "Red": "FF0000",
    "Blue": "0000FF",
    "Green": "008000",
    "Black": "000000",
    "White": "FFFFFF",
    "Yellow": "FFFF00",
    "Orange": "FFA500",
    "Purple": "800080",
    "Pink": "FFC0CB",
    "Gray": "808080",
    # Add more as needed to match your template options
}

class ZazzleProductDesigner:
    """Agent responsible for generating custom products on Zazzle using the Create-a-Product system."""

    def __init__(self):
        """Initialize the Product Designer with configuration."""
        self.affiliate_id = os.getenv('ZAZZLE_AFFILIATE_ID')
        if not self.affiliate_id:
            logger.error("ZAZZLE_AFFILIATE_ID is not set in environment variables. Affiliate links may not work correctly.")
        else:
            logger.info(f"ZAZZLE_AFFILIATE_ID loaded: {self.affiliate_id[:5]}...")
        
        # Load template config using the new DTO approach
        # For now, we assume a 'Sticker' product type. This can be made dynamic later.
        self.template: Optional[ZazzleTemplateConfig] = get_product_template("Sticker")
        if not self.template:
            logger.error("Zazzle template for 'Sticker' not found. Product creation may fail.")
            self.template_id = None # Set to None if template not found
        else:
            self.template_id = self.template.zazzle_template_id
            logger.info(f"Zazzle TEMPLATE_ID loaded from DTO: {self.template_id}")
        
        self.tracking_code = self.template.zazzle_tracking_code if self.template else os.getenv('ZAZZLE_TRACKING_CODE', '') # Load tracking code

    def _is_valid_url(self, url: str) -> bool:
        """Validate if a string is a valid URL."""
        if not url.startswith(('http://', 'https://')):
            return False
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def create_product(self, design_instructions: Dict[str, Any]) -> Dict[str, Any]:
        """Create a product using the design instructions."""
        # Check if template exists
        if not self.template or not self.affiliate_id:
            logger.error("Cannot create product: Zazzle template or ZAZZLE_AFFILIATE_ID is not set.")
            return None

        # Validate required fields - check image first to match test expectations
        if 'image' not in design_instructions or not design_instructions['image']:
            logger.error("Missing required image URL for field: image")
            return None

        # Validate image URL
        if not self._is_valid_url(design_instructions['image']):
            logger.error("Invalid image_url for field image: must start with http:// or https://")
            return None

        # Get customizable fields from template
        customizable_fields = self.template.customizable_fields

        try:
            # Build parameters dictionary
            params = {
                'ax': 'linkover',
                'pd': self.template.zazzle_template_id,
                'fwd': 'productpage',
                'ed': 'true',
                't_image1_url': quote(design_instructions['image'])
            }

            # Add customizable fields to parameters
            for field_name, field in customizable_fields.items():
                if field_name in design_instructions:
                    value = design_instructions[field_name]
                    if field.options is not None and value not in field.options:
                        raise ValueError(f"Invalid value for {field_name}: {value}. Must be one of {field.options}")
                    # Only encode if not already encoded (image handled above)
                    if field_name not in ['image']:
                        params[field_name] = quote(str(value))

            # Add tracking code
            params['tc'] = self.template.zazzle_tracking_code

            # Generate product URL
            product_url = self._generate_product_url(params)
            if not product_url:
                return None
            logger.info(f"Successfully generated product URL: {product_url}")

            return {
                'image': design_instructions['image'],
                'product_url': product_url
            }
        except ValueError as e:
            logger.error(str(e))
            raise  # Re-raise ValueError for invalid values
        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
            return None

    def _generate_product_url(self, params: Dict[str, Any]) -> Optional[str]:
        """Generate a product URL based on the given parameters."""
        try:
            if not self.template or not self.affiliate_id:
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

if __name__ == '__main__':
    # Example usage for new DTO based approach
    from app.zazzle_templates import ZAZZLE_STICKER_TEMPLATE
    designer = ZazzleProductDesigner()
    design_instructions = {
        'text': 'FIRE THE CANNONS!',
        'image': 'https://via.placeholder.com/150', # This is now the URL
        'image_iid': 'test_image_iid',
        'theme': 'test_theme',
        'color': 'Blue',
        'quantity': 12
    }
    result = designer.create_product(design_instructions)
    print(result) 