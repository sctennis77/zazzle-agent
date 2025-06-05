import os
import logging
from typing import Dict, List, Optional
from urllib.parse import quote, urljoin
from app.models import Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ZazzleAffiliateLinkerError(Exception):
    """Base exception for ZazzleAffiliateLinker errors."""
    pass

class InvalidProductDataError(ZazzleAffiliateLinkerError):
    """Raised when product data is invalid or missing required fields."""
    pass

class ZazzleAffiliateLinker:
    """Handles generation of Zazzle affiliate links."""
    
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

    def _validate_product_data(self, product_id: str, name: str) -> None:
        if not product_id:
            raise InvalidProductDataError("Product ID is required")
        if not name:
            raise InvalidProductDataError("Product name is required")

    def _construct_affiliate_link(self, product_id: str, name: str) -> str:
        """
        Construct the affiliate link URL for direct product links.
        
        Args:
            product_id: Zazzle product ID
            name: Product name
            
        Returns:
            Complete affiliate link URL.
        """
        try:
            # Format: https://www.zazzle.com/product/{product_id}?rf={affiliate_id}
            return f"https://www.zazzle.com/product/{product_id}?rf={self.affiliate_id}"
        except Exception as e:
            logger.error(f"Error constructing affiliate link: {e}")
            raise ZazzleAffiliateLinkerError(f"Failed to construct affiliate link: {e}")

    def generate_affiliate_link(self, product_id: str, name: str) -> str:
        """
        Generate a Zazzle affiliate link for a product.
        
        Args:
            product_id: Zazzle product ID
            name: Product name
        
        Returns:
            str: Complete affiliate link
            
        Raises:
            InvalidProductDataError: If product data is invalid
            ZazzleAffiliateLinkerError: For other errors during link generation
        """
        self._validate_product_data(product_id, name)
        try:
            affiliate_link = self._construct_affiliate_link(product_id, name)
            logger.info(f"Generated affiliate link for {name} ({product_id})")
            return affiliate_link
        except Exception as e:
            logger.error(f"Error generating affiliate link: {e}")
            raise ZazzleAffiliateLinkerError(f"Failed to generate affiliate link: {e}")

    def generate_links_batch(self, products: List[Product]) -> List[Product]:
        """
        Generate affiliate links for a batch of products.
        
        Args:
            products: List of Product objects
        
        Returns:
            list: List of Product objects with affiliate links added
            
        Raises:
            ZazzleAffiliateLinkerError: If batch processing fails
        """
        processed_products = []
        
        for product in products:
            try:
                affiliate_link = self.generate_affiliate_link(product.product_id, product.name)
                product.affiliate_link = affiliate_link
            except Exception as e:
                logger.error(f"Error processing product {product.product_id}: {e}")
                product.affiliate_link = None
            processed_products.append(product)
                
        return processed_products 