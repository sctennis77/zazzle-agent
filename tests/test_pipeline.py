import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.reddit_agent import RedditAgent
from app.image_generator import IMAGE_GENERATION_BASE_PROMPTS

# Add DB setup/teardown fixture
from app.db.database import Base, SessionLocal, engine
from app.db.models import PipelineRun
from app.models import PipelineConfig, ProductIdea, ProductInfo, RedditContext
from app.pipeline import Pipeline


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Drop and recreate all tables before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def pipeline():
    """Create a Pipeline instance for testing with all dependencies mocked."""
    config = PipelineConfig(
        model="dall-e-3",
        zazzle_template_id="template123",
        zazzle_tracking_code="tracking456",
        zazzle_affiliate_id="test_affiliate_id",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
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
    zazzle_designer.create_product.return_value = "https://example.com/product"
    affiliate_linker = AsyncMock()
    imgur_client = MagicMock()
    imgur_client.upload_image = AsyncMock()
    imgur_client.upload_image.return_value = "https://example.com/generated_image.jpg"
    return Pipeline(
        reddit_agent=reddit_agent,
        content_generator=content_generator,
        image_generator=image_generator,
        zazzle_designer=zazzle_designer,
        affiliate_linker=affiliate_linker,
        imgur_client=imgur_client,
        config=config,
    )


@pytest.fixture
def sample_product_idea():
    """Create a sample product idea for testing."""
    reddit_context = RedditContext(
        post_id="test_post_id",
        post_title="Test Post Title",
        post_url="https://reddit.com/test",
        subreddit="test_subreddit",
    )

    return ProductIdea(
        theme="test_theme",
        image_description="Test image description",
        design_instructions={"image": "https://example.com/image.jpg"},
        reddit_context=reddit_context,
        model="dall-e-3",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
    )


@pytest.mark.asyncio
async def test_process_product_idea(pipeline, sample_product_idea):
    """Test processing a single product idea through the pipeline."""
    # Mock the content generation
    pipeline.content_generator.generate_content.return_value = "Generated content"
    # Mock the image generation
    pipeline.image_generator.generate_image.return_value = (
        "https://example.com/generated_image.jpg",
        "/path/to/generated_image.jpg",
    )
    # Mock the product creation
    product_info = ProductInfo(
        product_id="test_id",
        name="Test Product",
        product_type="sticker",
        zazzle_template_id="template123",
        zazzle_tracking_code="tracking456",
        image_url="https://example.com/generated_image.jpg",
        product_url="https://example.com/product",
        theme="test_theme",
        model="dall-e-3",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
        reddit_context=sample_product_idea.reddit_context,
        design_instructions={
            "image": "https://example.com/image.jpg",
            "content": "Generated content",
        },
        image_local_path="/path/to/generated_image.jpg",
    )
    pipeline.zazzle_designer.create_product.return_value = product_info
    # Mock the affiliate link generation
    pipeline.affiliate_linker.generate_links_batch.return_value = [product_info]
    # Process the product idea
    result = await pipeline.process_product_idea(sample_product_idea)
    # Verify result
    assert isinstance(result, ProductInfo)
    assert result.product_id == "test_id"
    assert result.name == "Test Product"
    assert result.product_type == "sticker"
    assert result.image_url == "https://example.com/generated_image.jpg"
    assert result.theme == sample_product_idea.theme
    assert result.model == sample_product_idea.model
    assert result.prompt_version == sample_product_idea.prompt_version
    assert result.reddit_context == sample_product_idea.reddit_context


@pytest.mark.asyncio
async def test_run_pipeline_batch(pipeline):
    """Test processing a batch of product infos through the pipeline."""
    reddit_context = RedditContext(
        post_id="test_post_id",
        post_title="Test Post Title",
        post_url="https://reddit.com/test",
        subreddit="test_subreddit",
    )
    product_infos = [
        ProductInfo(
            product_id=f"test_id_{i}",
            name=f"Test Product {i}",
            product_type="sticker",
            zazzle_template_id="template123",
            zazzle_tracking_code="tracking456",
            image_url="https://example.com/generated_image.jpg",
            product_url=f"https://example.com/product_{i}",
            theme=f"theme{i+1}",
            model="dall-e-3",
            prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
            reddit_context=reddit_context,
            design_instructions={
                "image": f"https://example.com/image{i+1}.jpg",
                "content": "Generated content",
            },
            image_local_path=f"/path/to/generated_image_{i}.jpg",
        )
        for i in range(2)
    ]
    pipeline.reddit_agent.get_product_info.return_value = product_infos
    pipeline.affiliate_linker.generate_links_batch.side_effect = (
        lambda products: products
    )
    results = await pipeline.run_pipeline()
    assert len(results) == 2
    assert all(isinstance(result, ProductInfo) for result in results)


@pytest.mark.asyncio
async def test_run_pipeline_empty(pipeline):
    """Test that pipeline raises an exception when no products are generated."""
    pipeline.reddit_agent.get_product_info.return_value = []
    with pytest.raises(Exception) as exc_info:
        await pipeline.run_pipeline()
    assert "No products were generated" in str(exc_info.value)
    assert "pipeline_run_id" in str(exc_info.value)


@pytest.mark.asyncio
async def test_run_pipeline(mocker):
    """
    Test that the pipeline raises an exception when no products are generated.
    """
    # Mock dependencies
    mock_session = mocker.Mock()
    mock_session.query.return_value.get.return_value = None

    # Initialize pipeline
    pipeline = Pipeline(
        reddit_agent=AsyncMock(),
        content_generator=mocker.Mock(),
        image_generator=mocker.Mock(),
        zazzle_designer=mocker.Mock(),
        affiliate_linker=AsyncMock(),
        imgur_client=mocker.Mock(),
    )

    # Mock get_product_info to return an empty list
    pipeline.reddit_agent.get_product_info.return_value = []

    # Run pipeline and assert it raises an exception
    with pytest.raises(Exception) as exc_info:
        await pipeline.run_pipeline()
    assert "No products were generated" in str(exc_info.value)
    assert "pipeline_run_id" in str(exc_info.value)


@patch("app.image_generator.ImageGenerator.generate_image", new_callable=AsyncMock, return_value=("https://example.com/image.jpg", "/tmp/image.jpg"))
@patch("app.zazzle_product_designer.ZazzleProductDesigner.create_product", new_callable=AsyncMock)
@patch("app.agents.reddit_agent.RedditAgent._find_trending_post")
@patch("app.agents.reddit_agent.RedditAgent._determine_product_idea")
@pytest.mark.asyncio
async def test_pipeline_uses_correct_model(mock_determine, mock_find_post, mock_create_product, mock_generate_image):
    # Mock _find_trending_post to return a valid post
    mock_subreddit = MagicMock()
    mock_subreddit.display_name = "test_subreddit"
    mock_post = MagicMock(
        id="test_post_id",
        title="Test Post Title",
        url="https://reddit.com/test",
        subreddit=mock_subreddit,
        selftext="Test content",
        comment_summary="Test comment summary",
        permalink="/r/test/123",
    )
    mock_find_post.return_value = mock_post
    # Mock _determine_product_idea to return a valid product idea
    mock_determine.return_value = ProductIdea(
        theme="test_theme",
        image_description="Test image description",
        design_instructions={"image": "https://example.com/image.jpg"},
        reddit_context=RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        ),
        model="dall-e-2",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-2"]["version"],
    )
    # Mock create_product to return a valid ProductInfo
    mock_create_product.return_value = ProductInfo(
        product_id="test_id",
        name="Test Product",
        product_type="sticker",
        zazzle_template_id="template123",
        zazzle_tracking_code="tracking456",
        image_url="https://example.com/image.jpg",
        product_url="https://example.com/product",
        theme="test_theme",
        model="dall-e-2",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-2"]["version"],
        reddit_context=mock_determine.return_value.reddit_context,
        design_instructions={"image": "https://example.com/image.jpg"},
        image_local_path="/tmp/image.jpg",
    )
    # Create a pipeline with a specific model
    affiliate_linker = AsyncMock()
    product_info = mock_create_product.return_value
    affiliate_linker.generate_links_batch.return_value = [product_info]
    pipeline = Pipeline(
        reddit_agent=RedditAgent(config=PipelineConfig(model="dall-e-2",
                                                     zazzle_template_id="template123",
                                                     zazzle_tracking_code="tracking456",
                                                     zazzle_affiliate_id="test_affiliate_id",
                                                     prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-2"]["version"])),
        content_generator=MagicMock(),
        image_generator=MagicMock(),
        zazzle_designer=MagicMock(),
        affiliate_linker=affiliate_linker,
        imgur_client=MagicMock(),
        config=PipelineConfig(
            model="dall-e-2",
            zazzle_template_id="template123",
            zazzle_tracking_code="tracking456",
            zazzle_affiliate_id="test_affiliate_id",
            prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-2"]["version"],
        ),
    )
    # Run the pipeline
    await pipeline.run_pipeline()
    # Verify that the RedditAgent's ImageGenerator was initialized with the correct model
    assert pipeline.reddit_agent.image_generator.model == "dall-e-2"
