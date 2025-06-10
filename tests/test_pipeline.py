import pytest
from app.pipeline import Pipeline
from app.models import ProductIdea, RedditContext, ProductInfo, PipelineConfig
import os
import json

@pytest.fixture
def pipeline():
    """Create a Pipeline instance for testing."""
    config = PipelineConfig(
        model='dall-e-3',
        zazzle_template_id='template123',
        zazzle_tracking_code='tracking456',
        prompt_version='1.0.0'
    )
    return Pipeline(config)

@pytest.fixture
def sample_product_idea():
    """Create a sample product idea for testing."""
    reddit_context = RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit'
    )
    
    return ProductIdea(
        theme='test_theme',
        image_description='Test image description',
        design_instructions={'image': 'https://example.com/image.jpg'},
        reddit_context=reddit_context,
        model='dall-e-3',
        prompt_version='1.0.0'
    )

def test_process_product_idea(pipeline, sample_product_idea):
    """Test processing a single product idea through the pipeline."""
    # Mock the image generation
    def mock_generate_image(product_idea):
        return ProductInfo(
            product_id='test_id',
            name='Test Product',
            product_type='sticker',
            zazzle_template_id='template123',
            zazzle_tracking_code='tracking456',
            image_url='https://example.com/generated_image.jpg',
            product_url='https://example.com/product',
            theme='test_theme',
            model='dall-e-3',
            prompt_version='1.0.0',
            reddit_context=sample_product_idea.reddit_context,
            design_instructions={'image': 'https://example.com/image.jpg'},
            image_local_path='/path/to/generated_image.jpg'
        )
    
    pipeline.image_generator.generate_image = mock_generate_image
    
    # Mock the affiliate link generation
    def mock_generate_links(products):
        for product in products:
            product.affiliate_link = f"https://affiliate.example.com/{product.product_id}"
        return products
    
    pipeline.affiliate_linker.generate_links_batch = mock_generate_links
    
    # Process the product idea
    result = pipeline.process_product_idea(sample_product_idea)
    
    # Verify result
    assert isinstance(result, ProductInfo)
    assert result.product_id == 'test_id'
    assert result.name == 'Test Product'
    assert result.product_type == 'sticker'
    assert result.image_url == 'https://example.com/generated_image.jpg'
    assert result.affiliate_link == 'https://affiliate.example.com/test_id'
    assert result.theme == sample_product_idea.theme
    assert result.model == sample_product_idea.model
    assert result.prompt_version == sample_product_idea.prompt_version
    assert result.reddit_context == sample_product_idea.reddit_context

def test_process_product_ideas_batch(pipeline):
    """Test processing a batch of product ideas through the pipeline."""
    # Create sample product ideas
    reddit_context = RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit'
    )
    
    product_ideas = [
        ProductIdea(
            theme='theme1',
            image_description='Description 1',
            design_instructions={'image': 'https://example.com/image1.jpg'},
            reddit_context=reddit_context,
            model='dall-e-3',
            prompt_version='1.0.0'
        ),
        ProductIdea(
            theme='theme2',
            image_description='Description 2',
            design_instructions={'image': 'https://example.com/image2.jpg'},
            reddit_context=reddit_context,
            model='dall-e-3',
            prompt_version='1.0.0'
        )
    ]
    
    # Mock the image generation
    def mock_generate_images(product_ideas):
        return [
            ProductInfo(
                product_id=f'test_id_{i}',
                name=f'Test Product {i}',
                product_type='sticker',
                zazzle_template_id='template123',
                zazzle_tracking_code='tracking456',
                image_url=f'https://example.com/generated_image_{i}.jpg',
                product_url=f'https://example.com/product_{i}',
                theme=idea.theme,
                model='dall-e-3',
                prompt_version='1.0.0',
                reddit_context=reddit_context,
                design_instructions={'image': f'https://example.com/image{i}.jpg'},
                image_local_path=f'/path/to/generated_image_{i}.jpg'
            )
            for i, idea in enumerate(product_ideas)
        ]
    
    pipeline.image_generator.generate_images_batch = mock_generate_images
    
    # Mock the affiliate link generation
    def mock_generate_links(products):
        for product in products:
            product.affiliate_link = f"https://affiliate.example.com/{product.product_id}"
        return products
    
    pipeline.affiliate_linker.generate_links_batch = mock_generate_links
    
    # Process the product ideas
    results = pipeline.process_product_ideas_batch(product_ideas)
    
    # Verify results
    assert len(results) == 2
    assert all(isinstance(result, ProductInfo) for result in results)
    assert results[0].theme == 'theme1'
    assert results[1].theme == 'theme2'
    assert results[0].affiliate_link == 'https://affiliate.example.com/test_id_0'
    assert results[1].affiliate_link == 'https://affiliate.example.com/test_id_1'

def test_process_product_ideas_batch_empty(pipeline):
    """Test processing an empty batch of product ideas."""
    results = pipeline.process_product_ideas_batch([])
    assert len(results) == 0 