import os
import logging
from typing import Dict, List, Optional
from urllib.parse import quote, urljoin
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProductData:
    """Data class to hold product information."""
    title: str
    product_id: str
    affiliate_id: str

class ZazzleAffiliateLinkerError(Exception):
    """Base exception for ZazzleAffiliateLinker errors."""
    pass

class InvalidProductDataError(ZazzleAffiliateLinkerError):
    """Raised when product data is invalid or missing required fields."""
    pass

class ZazzleAffiliateLinker:
    """Handles generation of Zazzle affiliate links."""
    
    BASE_URL = "https://www.zazzle.com/shop"
    
    def __init__(self, affiliate_id: str):
        """
        Initialize the ZazzleAffiliateLinker.
        
        Args:
            affiliate_id: The Zazzle affiliate ID to use in generated links.
            
        Raises:
            ValueError: If affiliate_id is empty or None.
        """
        if not affiliate_id:
            raise ValueError("Affiliate ID cannot be empty")
            
        logger.info("Initializing ZazzleAffiliateLinker")
        self.affiliate_id = affiliate_id

    def _validate_product_data(self, product_data: Dict[str, str]) -> ProductData:
        """
        Validate and convert product data to ProductData object.
        
        Args:
            product_data: Dictionary containing product information.
            
        Returns:
            ProductData object with validated data.
            
        Raises:
            InvalidProductDataError: If required fields are missing or invalid.
        """
        try:
            title = product_data.get('title')
            product_id = product_data.get('product_id')
            
            if not title or not product_id:
                missing_fields = []
                if not title:
                    missing_fields.append('title')
                if not product_id:
                    missing_fields.append('product_id')
                raise InvalidProductDataError(f"Missing required fields: {', '.join(missing_fields)}")
                
            return ProductData(
                title=title,
                product_id=product_id,
                affiliate_id=self.affiliate_id
            )
        except Exception as e:
            if not isinstance(e, InvalidProductDataError):
                raise InvalidProductDataError(f"Error validating product data: {str(e)}")
            raise

    def _construct_affiliate_link(self, product: ProductData) -> str:
        """
        Construct the affiliate link URL.
        
        Args:
            product: ProductData object containing validated product information.
            
        Returns:
            Complete affiliate link URL.
        """
        try:
            encoded_title = quote(product.title)
            
            # Construct query parameters
            params = {
                'rf': product.affiliate_id,
                'product_id': product.product_id,
                'title': encoded_title
            }
            
            # Build query string
            query_string = '&'.join(f"{k}={v}" for k, v in params.items())
            
            # Construct final URL
            affiliate_link = f"{self.BASE_URL}?{query_string}"
            
            logger.debug(f"Generated affiliate link: {affiliate_link}")
            return affiliate_link
            
        except Exception as e:
            logger.error(f"Error constructing affiliate link: {str(e)}")
            raise ZazzleAffiliateLinkerError(f"Failed to construct affiliate link: {str(e)}")

    def generate_affiliate_link(self, product_data: Dict[str, str]) -> str:
        """
        Generate a Zazzle affiliate link for a product.
        
        Args:
            product_data: Dictionary containing product information
                - title: Product title
                - product_id: Zazzle product ID
        
        Returns:
            str: Complete affiliate link
            
        Raises:
            InvalidProductDataError: If product data is invalid
            ZazzleAffiliateLinkerError: For other errors during link generation
        """
        try:
            # Validate and convert product data
            product = self._validate_product_data(product_data)
            
            # Generate the affiliate link
            affiliate_link = self._construct_affiliate_link(product)
            
            logger.info(f"Generated affiliate link for {product.title} ({product.product_id})")
            return affiliate_link
            
        except InvalidProductDataError as e:
            logger.error(f"Invalid product data: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating affiliate link: {str(e)}")
            raise ZazzleAffiliateLinkerError(f"Failed to generate affiliate link: {str(e)}")

    def generate_links_batch(self, products: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Generate affiliate links for a batch of products.
        
        Args:
            products: List of product dictionaries
        
        Returns:
            list: List of dictionaries with affiliate links added
            
        Raises:
            ZazzleAffiliateLinkerError: If batch processing fails
        """
        processed_products = []
        
        for product in products:
            try:
                affiliate_link = self.generate_affiliate_link(product)
                product['affiliate_link'] = affiliate_link
                processed_products.append(product)
            except Exception as e:
                logger.error(f"Error processing product in batch: {str(e)}")
                # Continue processing other products even if one fails
                continue
                
        if not processed_products:
            raise ZazzleAffiliateLinkerError("No products were successfully processed")
            
        return processed_products 