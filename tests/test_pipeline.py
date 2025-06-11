import pytest
from unittest.mock import MagicMock, AsyncMock
from app.pipeline import Pipeline
from app.models import ProductIdea, RedditContext, ProductInfo, PipelineConfig
import os
import json

@pytest.fixture
def pipeline():
    """Create a Pipeline instance for testing with all dependencies mocked."""
    config = PipelineConfig(
        model='dall-e-3',
        zazzle_template_id='template123',
        zazzle_tracking_code='tracking456',
        prompt_version='1.0.0'
    )
    reddit_agent = MagicMock()
    reddit_agent.get_product_info = AsyncMock()
    content_generator = MagicMock()
    content_generator.generate_content = AsyncMock()
    image_generator = MagicMock()
    image_generator.generate_image = AsyncMock()
    image_generator.generate_images_batch = AsyncMock()
    zazzle_designer = MagicMock()
    zazzle_designer.create_product = AsyncMock()
    affiliate_linker = MagicMock()
    affiliate_linker.generate_links_batch = AsyncMock()
    imgur_client = MagicMock()
    return Pipeline(
        reddit_agent=reddit_agent,
        content_generator=content_generator,
        image_generator=image_generator,
        zazzle_designer=zazzle_designer,
        affiliate_linker=affiliate_linker,
        imgur_client=imgur_client,
        config=config
    )

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

@pytest.mark.asyncio
async def test_process_product_idea(pipeline, sample_product_idea):
    """Test processing a single product idea through the pipeline."""
    # Mock the content generation
    pipeline.content_generator.generate_content.return_value = "Generated content"
    # Mock the image generation
    pipeline.image_generator.generate_image.return_value = ("https://example.com/generated_image.jpg", "/path/to/generated_image.jpg")
    # Mock the product creation
    product_info = ProductInfo(
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
        design_instructions={'image': 'https://example.com/image.jpg', 'content': 'Generated content'},
        image_local_path='/path/to/generated_image.jpg'
    )
    pipeline.zazzle_designer.create_product.return_value = product_info
    # Mock the affiliate link generation
    pipeline.affiliate_linker.generate_links_batch.return_value = [product_info]
    # Process the product idea
    result = await pipeline.process_product_idea(sample_product_idea)
    # Verify result
    assert isinstance(result, ProductInfo)
    assert result.product_id == 'test_id'
    assert result.name == 'Test Product'
    assert result.product_type == 'sticker'
    assert result.image_url == 'https://example.com/generated_image.jpg'
    assert result.theme == sample_product_idea.theme
    assert result.model == sample_product_idea.model
    assert result.prompt_version == sample_product_idea.prompt_version
    assert result.reddit_context == sample_product_idea.reddit_context

@pytest.mark.asyncio
async def test_run_pipeline_batch(pipeline):
    """Test processing a batch of product infos through the pipeline."""
    reddit_context = RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit'
    )
    product_infos = [
        ProductInfo(
            product_id=f'test_id_{i}',
            name=f'Test Product {i}',
            product_type='sticker',
            zazzle_template_id='template123',
            zazzle_tracking_code='tracking456',
            image_url='https://example.com/generated_image.jpg',
            product_url=f'https://example.com/product_{i}',
            theme=f'theme{i+1}',
            model='dall-e-3',
            prompt_version='1.0.0',
            reddit_context=reddit_context,
            design_instructions={'image': f'https://example.com/image{i+1}.jpg', 'content': 'Generated content'},
            image_local_path=f'/path/to/generated_image_{i}.jpg'
        )
        for i in range(2)
    ]
    pipeline.reddit_agent.get_product_info.return_value = product_infos
    pipeline.affiliate_linker.generate_links_batch.side_effect = lambda products: products
    results = await pipeline.run_pipeline()
    assert len(results) == 2
    assert all(isinstance(result, ProductInfo) for result in results)

@pytest.mark.asyncio
async def test_run_pipeline_empty(pipeline):
    """Test processing an empty batch of product ideas."""
    pipeline.reddit_agent.get_product_info.return_value = []
    results = await pipeline.run_pipeline()
    assert len(results) == 0 