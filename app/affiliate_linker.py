import os
import logging
from typing import Dict
from urllib.parse import quote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ZazzleAffiliateLinker:
    def __init__(self, affiliate_id: str):
        logger.info("Initializing ZazzleAffiliateLinker")
        self.affiliate_id = affiliate_id
        if not self.affiliate_id:
            logger.warning("Zazzle Affiliate ID not provided. Affiliate links will not be generated correctly.")
        self.base_url = "https://www.zazzle.com/create_your_own_product"

    def generate_affiliate_link(self, product_data: Dict[str, str]) -> str:
        """
        Generate a Zazzle affiliate link for a product.
        
        Args:
            product_data: Dictionary containing product information
                - title: Product title
                - product_id: Zazzle product ID
        
        Returns:
            str: Complete affiliate link
        """
        try:
            # Ensure required keys exist, will raise KeyError if not
            title = product_data['title']
            product_id = product_data['product_id']

            # Basic URL encoding for the title. More sophisticated encoding might be needed.
            # Replacing spaces with + is a common form-urlencoded approach for query strings.
            # For path segments, standard URL encoding (%20 for space) is typical.
            # Zazzle URLs seem to replace spaces with underscores or hyphens in the title part,
            # but for the portion after the product ID, standard encoding is safer.
            # Let's use quote for simplicity, which handles most characters.
            encoded_title = quote(title)
            
            # Construct the affiliate link
            affiliate_link = (
                f"{self.base_url}?"
                f"rf={self.affiliate_id}&"
                f"product_id={product_id}&"
                f"title={encoded_title}"
            )
            
            logger.info(f"Generated affiliate link for {title} ({product_id})")
            return affiliate_link
            
        except KeyError as e:
            logger.error(f"Error generating affiliate link: Missing key {e}")
            # Re-raise the exception so the test can catch it
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred during affiliate link generation: {e}")
            return "Error generating affiliate link."

    def generate_links_batch(self, products: list) -> list:
        """
        Generate affiliate links for a batch of products.
        
        Args:
            products: List of product dictionaries
        
        Returns:
            list: List of dictionaries with affiliate links added
        """
        processed_products = []
        
        for product in products:
            affiliate_link = self.generate_affiliate_link(product)
            product['affiliate_link'] = affiliate_link
            processed_products.append(product)
            
        return processed_products 