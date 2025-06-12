"""
Affiliate link generation module for the Zazzle Agent application.

This module provides functionality for generating Zazzle affiliate links for products.
It supports both single and batch link generation, with error handling for invalid data.

The module handles:
- Validation of product data
- Construction of affiliate links with proper formatting
- Batch processing of multiple products
- Error handling and logging
"""

import logging
from typing import List, Optional
from app.models import ProductInfo, AffiliateLinker
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class ZazzleAffiliateLinkerError(Exception):
    """Base exception for ZazzleAffiliateLinker errors."""
    pass

class InvalidProductDataError(ZazzleAffiliateLinkerError):
    """Raised when product data is invalid or missing required fields."""
    pass

class ZazzleAffiliateLinker:
    """
    Handles generation of Zazzle affiliate links.
    
    This class provides methods to generate affiliate links for individual products
    or batches of products, ensuring required data is present and handling errors.
    
    The class supports:
    - Single product link generation
    - Batch processing of multiple products
    - Validation of required product data
    - Error handling and logging
    - Custom affiliate ID configuration
    """
    
    def __init__(self, zazzle_affiliate_id: str, zazzle_tracking_code: str):
        """
        Initialize the ZazzleAffiliateLinker.
        
        Args:
            zazzle_affiliate_id: The Zazzle affiliate ID
            zazzle_tracking_code: The tracking code for affiliate links
        """
        self.affiliate_linker = AffiliateLinker(
            zazzle_affiliate_id=zazzle_affiliate_id,
            zazzle_tracking_code=zazzle_tracking_code
        )
        logger.info(f"Initialized ZazzleAffiliateLinker with affiliate ID: {zazzle_affiliate_id}")

    def _validate_product_data(self, product_id: str, name: str) -> None:
        """
        Validate that product data contains required fields.
        
        Args:
            product_id (str): The product's unique identifier from Zazzle
            name (str): The product's display name
        
        Raises:
            InvalidProductDataError: If product_id or name is empty or None
        """
        if not product_id:
            raise InvalidProductDataError("Product ID is required")
        if not name:
            raise InvalidProductDataError("Product name is required")

    def _construct_affiliate_link(self, product_id: str, name: str) -> str:
        """
        Construct the affiliate link URL for direct product links.
        
        Args:
            product_id (str): Zazzle product ID
            name (str): Product name (used for logging purposes)
        
        Returns:
            str: Complete affiliate link URL in format:
                https://www.zazzle.com/product/{product_id}?rf={affiliate_id}
        
        Raises:
            ZazzleAffiliateLinkerError: If link construction fails
        """
        try:
            return f"https://www.zazzle.com/product/{product_id}?rf={self.affiliate_linker.zazzle_affiliate_id}"
        except Exception as e:
            logger.error(f"Error constructing affiliate link: {e}")
            raise ZazzleAffiliateLinkerError(f"Failed to construct affiliate link: {e}")

    async def _generate_affiliate_link(self, product: ProductInfo) -> str:
        """
        Generate a Zazzle affiliate link for a product.
        
        Args:
            product (ProductInfo): ProductInfo object containing product details
        
        Returns:
            str: Complete affiliate link URL
        
        Raises:
            InvalidProductDataError: If product data is invalid or missing required fields
            ZazzleAffiliateLinkerError: For other errors during link generation
        """
        self._validate_product_data(product.product_id, product.name)
        try:
            affiliate_link = self._construct_affiliate_link(product.product_id, product.name)
            logger.info(f"Generated affiliate link for {product.name} ({product.product_id})")
            return affiliate_link
        except Exception as e:
            logger.error(f"Error generating affiliate link: {e}")
            raise ZazzleAffiliateLinkerError(f"Failed to generate affiliate link: {e}")

    async def generate_links_batch(self, products: List[ProductInfo]) -> List[ProductInfo]:
        """
        Generate affiliate links for a batch of products.
        
        Args:
            products: List of ProductInfo objects to generate links for
            
        Returns:
            List[ProductInfo]: List of products with affiliate links added
        """
        for product in products:
            try:
                affiliate_link = self.affiliate_linker.compose_affiliate_link(product.product_url)
                product.affiliate_link = affiliate_link
                logger.info(f"Generated affiliate link for {product.name} ({product.product_id})")
            except Exception as e:
                logger.error(f"Failed to generate affiliate link for {product.name}: {str(e)}")
                raise
        return products 