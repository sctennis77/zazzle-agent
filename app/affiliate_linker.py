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
from typing import List
from app.models import ProductInfo
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
    
    def __init__(self, affiliate_id=None):
        """
        Initialize the ZazzleAffiliateLinker.
        
        Args:
            affiliate_id (str, optional): The Zazzle affiliate ID to use in generated links.
                If not provided, defaults to 'test_affiliate_id'.
            
        Raises:
            ValueError: If affiliate_id is empty or None.
        """
        self.affiliate_id = affiliate_id or 'test_affiliate_id'
        logger.info("Initializing ZazzleAffiliateLinker")

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
            return f"https://www.zazzle.com/product/{product_id}?rf={self.affiliate_id}"
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
            products (List[ProductInfo]): List of ProductInfo objects to process
        
        Returns:
            List[ProductInfo]: List of ProductInfo objects with affiliate links added.
                Products that fail to process will have affiliate_link set to None.
        
        Raises:
            ZazzleAffiliateLinkerError: If batch processing fails completely
        """
        processed_products = []
        for product in products:
            try:
                affiliate_link = await self._generate_affiliate_link(product)
                product.affiliate_link = affiliate_link
            except Exception as e:
                logger.error(f"Error processing product {product.product_id}: {e}")
                product.affiliate_link = None
            processed_products.append(product)
        return processed_products 