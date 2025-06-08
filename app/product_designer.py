import os
import logging
from typing import Dict, Optional
from urllib.parse import quote
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

    def create_product(self, product_info: Dict) -> Optional[Dict]:
        """Create a custom product using Zazzle's Create-a-Product system, based on the template.

        Args:
            product_info: A dictionary containing the dynamic values for customizable fields
                          (e.g., {'text': 'My Custom Text', 'image': 'image_iid'}).

        Returns:
            Dict containing the product URL and other relevant info, or None if creation fails.
        """
        try:
            if not self.template or not self.affiliate_id:
                logger.error("Cannot create product: Zazzle template or ZAZZLE_AFFILIATE_ID is not set.")
                return None

            # Validate required customizable fields from the template
            for field_name, field_config in self.template.customizable_fields.items():
                if field_config.type == "text" and product_info.get(field_name) is None:
                    logger.error(f"Missing required text field: {field_name}")
                    return None
                if field_config.type == "image":
                    if not product_info.get(field_name):
                         logger.error(f"Missing required image URL for field: {field_name}")
                         return None
                    # Basic validation for image_url if provided
                    image_url = product_info.get(field_name, '')
                    if not (image_url.startswith('http://') or image_url.startswith('https://')):
                        logger.error(f"Invalid image_url for field {field_name}: must start with http:// or https://")
                        return None

            # Construct the deep link URL with product details dynamically
            base_url = f"https://www.zazzle.com/api/create/at-{self.affiliate_id}"
            params = {
                'ax': 'linkover',
                'pd': self.template.zazzle_template_id,
                'fwd': 'productpage',
                'ed': 'true', # Allow customization
            }

            # Dynamically add customizable fields to params
            for field_name, field_config in self.template.customizable_fields.items():
                if field_config.type == "text" and product_info.get(field_name) is not None:
                    # Zazzle uses t_<field_name>1_txt for text fields
                    # Use quote() to properly encode the text value
                    text_value = quote(product_info[field_name])
                    params[f't_{field_name}1_txt'] = text_value
                elif field_config.type == "image" and product_info.get(field_name) is not None:
                    # Zazzle uses t_<field_name>1_url for image fields with external URLs
                    # The image URL itself needs to be encoded for the URL parameter
                    image_url_encoded = quote(product_info[field_name], safe='')
                    params[f't_{field_name}1_url'] = image_url_encoded

            # Add other common parameters if present in product_info
            if product_info.get('color'):
                # Use quote() to properly encode the color value
                color_value = quote(product_info['color'])
                params['color'] = color_value
            if product_info.get('quantity'):
                params['quantity'] = product_info['quantity']
            
            # Add tracking code from template
            if self.template.zazzle_tracking_code:
                params['tc'] = self.template.zazzle_tracking_code
            
            # Construct the final URL - no need to quote values again since they're already encoded
            query_string = '&'.join(f"{k}={v}" for k, v in params.items())
            product_url = f"{base_url}?{query_string}"

            # Validate the URL (basic check)
            if not product_url.startswith('https://www.zazzle.com/api/create/at-'):
                logger.error("Invalid product URL generated")
                return None

            logger.info(f"Successfully generated product URL: {product_url}")
            
            # Return the product info with the CAP URL, including all original product_info
            return {**product_info, 'product_url': product_url}
        
        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
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