"""
Pipeline module for the Zazzle Agent application.

This module provides a mock pipeline for processing product ideas into product info objects.
It simulates image generation and affiliate link generation for testing and development purposes.
"""

from app.models import ProductIdea, ProductInfo, PipelineConfig

class Pipeline:
    """
    Mock pipeline for processing product ideas into product info objects.
    
    This class simulates the main steps of the product creation pipeline:
    1. Image generation (mocked)
    2. Affiliate link generation (mocked)
    3. Batch processing for multiple product ideas
    """
    def __init__(self, config: PipelineConfig):
        """
        Initialize the pipeline with a configuration.
        
        Args:
            config: PipelineConfig object with pipeline settings
        """
        self.config = config
        self.image_generator = self
        self.affiliate_linker = self

    def generate_image(self, product_idea: ProductIdea) -> ProductInfo:
        """
        Simulate image generation for a product idea.
        
        Args:
            product_idea: ProductIdea object
        
        Returns:
            ProductInfo object with mock data
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

    def generate_images_batch(self, product_ideas):
        """
        Simulate batch image generation for multiple product ideas.
        
        Args:
            product_ideas: List of ProductIdea objects
        
        Returns:
            List of ProductInfo objects
        """
        return [self.generate_image(idea) for idea in product_ideas]

    def generate_links_batch(self, products):
        """
        Simulate affiliate link generation for a batch of products.
        
        Args:
            products: List of ProductInfo objects
        
        Returns:
            List of ProductInfo objects with affiliate_link set
        """
        for product in products:
            product.affiliate_link = f'https://affiliate.example.com/{product.product_id}'
        return products

    def process_product_idea(self, product_idea):
        """
        Process a single product idea through the pipeline.
        
        Args:
            product_idea: ProductIdea object
        
        Returns:
            ProductInfo object with affiliate link
        """
        product = self.generate_image(product_idea)
        self.generate_links_batch([product])
        return product

    def process_product_ideas_batch(self, product_ideas):
        """
        Process a batch of product ideas through the pipeline.
        
        Args:
            product_ideas: List of ProductIdea objects
        
        Returns:
            List of ProductInfo objects with affiliate links
        """
        products = self.generate_images_batch(product_ideas)
        self.generate_links_batch(products)
        return products 