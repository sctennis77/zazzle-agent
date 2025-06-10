"""
Pipeline module for the Zazzle Agent application.

This module provides a mock pipeline for processing product ideas into product info objects.
It simulates image generation and affiliate link generation for testing and development purposes.

The module handles:
- Mock image generation for product ideas
- Mock affiliate link generation
- Single product idea processing
- Batch processing of multiple product ideas
- Pipeline configuration management
"""

from typing import List, Optional
from app.models import ProductIdea, ProductInfo, PipelineConfig

class Pipeline:
    """
    Mock pipeline for processing product ideas into product info objects.
    
    This class simulates the main steps of the product creation pipeline:
    1. Image generation (mocked)
    2. Affiliate link generation (mocked)
    3. Batch processing for multiple product ideas
    
    The class supports:
    - Single product idea processing
    - Batch processing of multiple ideas
    - Configurable pipeline settings
    - Mock data generation for testing
    """
    
    def __init__(self, config: PipelineConfig):
        """
        Initialize the pipeline with a configuration.
        
        Args:
            config (PipelineConfig): PipelineConfig object with pipeline settings
                and configuration parameters
        """
        self.config = config
        self.image_generator = self
        self.affiliate_linker = self

    def generate_image(self, product_idea: ProductIdea) -> ProductInfo:
        """
        Simulate image generation for a product idea.
        
        Args:
            product_idea (ProductIdea): ProductIdea object containing design
                instructions and metadata
        
        Returns:
            ProductInfo: ProductInfo object with mock data including:
                - Product ID and name
                - Template and tracking information
                - Image and product URLs
                - Theme and model details
                - Design instructions
                - Local image path
        """
        return ProductInfo(
            product_id='mock_id',
            name='Mock Product',
            product_type='sticker',
            zazzle_template_id='template123',
            zazzle_tracking_code='tracking456',
            image_url='https://example.com/image.jpg',
            product_url='https://example.com/product',
            theme=product_idea.theme,
            model=product_idea.model,
            prompt_version=product_idea.prompt_version,
            reddit_context=product_idea.reddit_context,
            design_instructions=product_idea.design_instructions,
            image_local_path='/tmp/mock.jpg'
        )

    def generate_images_batch(self, product_ideas: List[ProductIdea]) -> List[ProductInfo]:
        """
        Simulate batch image generation for multiple product ideas.
        
        Args:
            product_ideas (List[ProductIdea]): List of ProductIdea objects to process
        
        Returns:
            List[ProductInfo]: List of ProductInfo objects with mock data for each idea
        """
        return [self.generate_image(idea) for idea in product_ideas]

    def generate_links_batch(self, products: List[ProductInfo]) -> List[ProductInfo]:
        """
        Simulate affiliate link generation for a batch of products.
        
        Args:
            products (List[ProductInfo]): List of ProductInfo objects to process
        
        Returns:
            List[ProductInfo]: List of ProductInfo objects with affiliate_link set
                to mock URLs
        """
        for product in products:
            product.affiliate_link = f'https://affiliate.example.com/{product.product_id}'
        return products

    def process_product_idea(self, product_idea: ProductIdea) -> ProductInfo:
        """
        Process a single product idea through the pipeline.
        
        Args:
            product_idea (ProductIdea): ProductIdea object to process
        
        Returns:
            ProductInfo: ProductInfo object with mock data and affiliate link
        """
        product = self.generate_image(product_idea)
        self.generate_links_batch([product])
        return product

    def process_product_ideas_batch(self, product_ideas: List[ProductIdea]) -> List[ProductInfo]:
        """
        Process a batch of product ideas through the pipeline.
        
        Args:
            product_ideas (List[ProductIdea]): List of ProductIdea objects to process
        
        Returns:
            List[ProductInfo]: List of ProductInfo objects with mock data and
                affiliate links for each idea
        """
        products = self.generate_images_batch(product_ideas)
        self.generate_links_batch(products)
        return products 