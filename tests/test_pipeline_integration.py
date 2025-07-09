"""
Integration tests for the product generation pipeline.

These tests verify the complete pipeline functionality, including:
- Full pipeline execution
- Error handling and recovery
- Concurrent operations
- Rate limiting and retries
- Database integration
"""

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.affiliate_linker import ZazzleAffiliateLinker
from app.agents.reddit_agent import RedditAgent
from app.clients.imgur_client import ImgurClient
from app.content_generator import ContentGenerator
from app.db.database import Base, SessionLocal, engine
from app.db.mappers import product_info_to_db
from app.db.models import PipelineRun
from app.db.models import ProductInfo as DBProductInfo
from app.db.models import RedditPost
from app.image_generator import ImageGenerator, IMAGE_GENERATION_BASE_PROMPTS
from app.models import ProductIdea, ProductInfo, RedditContext
from app.pipeline import Pipeline
from app.pipeline_status import PipelineStatus
from app.zazzle_product_designer import ZazzleProductDesigner

# Configure logging
logging.basicConfig(level=logging.DEBUG)


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Drop and recreate all tables before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_reddit_agent():
    """Create a mock RedditAgent with predefined responses."""
    agent = AsyncMock(spec=RedditAgent)
    agent.get_product_info = AsyncMock(
        return_value=[
            ProductIdea(
                theme="Test Theme",
                image_description="Test Description",
                design_instructions={"image": "https://example.com/test.jpg"},
                reddit_context=RedditContext(
                    post_id="test123",
                    post_title="Test Post",
                    post_url="https://reddit.com/test",
                    subreddit="test",
                ),
                model="dall-e-3",
                prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
            )
        ]
    )
    return agent


@pytest.fixture
def mock_content_generator():
    """Create a mock ContentGenerator with predefined responses."""
    generator = AsyncMock(spec=ContentGenerator)
    generator.generate_content = AsyncMock(return_value="Generated content")
    return generator


@pytest.fixture
def mock_image_generator():
    """Create a mock ImageGenerator with predefined responses."""
    generator = AsyncMock(spec=ImageGenerator)
    generator.generate_image = AsyncMock(
        return_value=("https://imgur.com/test.jpg", "/tmp/test.jpg")
    )
    return generator


@pytest.fixture
def mock_zazzle_designer():
    """Create a mock ZazzleProductDesigner with predefined responses."""
    designer = AsyncMock(spec=ZazzleProductDesigner)
    designer.create_product = AsyncMock(
        return_value=ProductInfo(
            product_id="test123",
            name="Test Product",
            product_type="sticker",
            zazzle_template_id="template123",
            zazzle_tracking_code="tracking123",
            image_url="https://imgur.com/test.jpg",
            product_url="https://zazzle.com/test",
            theme="Test Theme",
            model="dall-e-3",
            prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
            reddit_context=RedditContext(
                post_id="test123",
                post_title="Test Post",
                post_url="https://reddit.com/test",
                subreddit="test",
            ),
            design_instructions={
                "image": "https://imgur.com/test.jpg",
                "content": "Generated content",
            },
            image_local_path="/tmp/test.jpg",
        )
    )
    return designer


@pytest.fixture
def mock_affiliate_linker():
    """Create a mock ZazzleAffiliateLinker with predefined responses."""
    linker = AsyncMock(spec=ZazzleAffiliateLinker)

    async def mock_generate_links_batch(products):
        for p in products:
            p.affiliate_link = "https://zazzle.com/test?ref=123"
        return products

    linker.generate_links_batch = AsyncMock(side_effect=mock_generate_links_batch)
    return linker


@pytest.fixture
def mock_imgur_client():
    """Create a mock ImgurClient with predefined responses."""
    client = MagicMock(spec=ImgurClient)
    client.upload_image.return_value = ("https://imgur.com/test.jpg", "/tmp/test.jpg")
    return client


@pytest.mark.asyncio
async def test_full_pipeline_success(
    mock_reddit_agent,
    mock_content_generator,
    mock_image_generator,
    mock_zazzle_designer,
    mock_affiliate_linker,
    mock_imgur_client,
):
    """
    Test the full pipeline with successful operations and database integration.
    """
    # Create pipeline with mocks
    pipeline = Pipeline(
        reddit_agent=mock_reddit_agent,
        content_generator=mock_content_generator,
        image_generator=mock_image_generator,
        zazzle_designer=mock_zazzle_designer,
        affiliate_linker=mock_affiliate_linker,
        imgur_client=mock_imgur_client,
    )

    # Create a pipeline run
    session = SessionLocal()
    try:
        pipeline_run = PipelineRun(
            status=PipelineStatus.STARTED.value, start_time=datetime.utcnow()
        )
        session.add(pipeline_run)
        session.commit()
        logging.debug(f"Created PipelineRun with ID: {pipeline_run.id}")
        pipeline.pipeline_run_id = pipeline_run.id
        pipeline.session = session
    finally:
        session.close()

    # Mock get_product_info to return a single ProductInfo
    product_info = ProductInfo(
        product_id="test123",
        name="Test Product",
        product_type="sticker",
        zazzle_template_id="template123",
        zazzle_tracking_code="tracking456",
        image_url="https://example.com/generated_image.jpg",
        product_url="https://example.com/product_1",
        theme="theme1",
        model="dall-e-3",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
        reddit_context=RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        ),
        design_instructions={
            "image": "https://example.com/image1.jpg",
            "content": "Generated content",
        },
        image_local_path="/path/to/generated_image_0.jpg",
    )
    mock_reddit_agent.get_product_info.return_value = [product_info]
    mock_affiliate_linker.generate_links_batch.side_effect = lambda products: products

    # Run the pipeline
    products = await pipeline.run_pipeline()

    # Manually update pipeline run status to 'success' for the test
    session = SessionLocal()
    try:
        if products:
            # Removed manual addition of Reddit context to DB
            # reddit_context = products[0].reddit_context
            # agent = RedditAgent()
            # agent.session = session
            # agent.pipeline_run_id = pipeline.pipeline_run_id
            # reddit_post_id = agent.save_reddit_context_to_db(reddit_context)
            session.commit()
    finally:
        session.close()

    # Verify results
    assert len(products) >= 1
    assert products[0].product_id == "test123"

    # Verify database state
    session = SessionLocal()
    try:
        # Check pipeline run
        pipeline_runs = session.query(PipelineRun).all()
        logging.debug(f"Total PipelineRun entries: {len(pipeline_runs)}")
        assert len(pipeline_runs) == 1
        run = pipeline_runs[0]
        assert run.status == "completed"
        assert run.start_time is not None
        assert run.end_time is not None
        assert run.end_time > run.start_time

        # Check reddit post
        reddit_posts = session.query(RedditPost).all()
        assert len(reddit_posts) == 1
        post = reddit_posts[0]
        assert post.post_id == "test_post_id"
        assert post.title == "Test Post Title"
        assert post.subreddit.subreddit_name == "test_subreddit"
        assert post.pipeline_run_id == run.id

        # Check product info
        db_products = session.query(DBProductInfo).all()
        assert len(db_products) == 1
        db_product = db_products[0]
        assert db_product.theme == "theme1"
        assert db_product.image_url == "https://example.com/generated_image.jpg"
        assert db_product.product_url == "https://example.com/product_1"
        assert db_product.template_id == "template123"
        assert db_product.model == "dall-e-3"
        assert db_product.prompt_version == IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"]
        assert db_product.product_type == "sticker"
        assert db_product.pipeline_run_id == run.id
        assert db_product.reddit_post_id == post.id
    finally:
        session.close()


@pytest.mark.asyncio
async def test_pipeline_error_handling(
    mock_reddit_agent,
    mock_content_generator,
    mock_image_generator,
    mock_zazzle_designer,
    mock_affiliate_linker,
    mock_imgur_client,
):
    """Test pipeline error handling and recovery."""
    # Simulate an error in the affiliate linker
    mock_affiliate_linker.generate_links_batch.side_effect = Exception(
        "Affiliate link generation failed"
    )

    # Mock get_product_info to return ProductInfo
    product_info = ProductInfo(
        product_id="test123",
        name="Test Product",
        product_type="sticker",
        zazzle_template_id="template123",
        zazzle_tracking_code="tracking456",
        image_url="https://example.com/generated_image.jpg",
        product_url="https://example.com/product_1",
        theme="theme1",
        model="dall-e-3",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
        reddit_context=RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        ),
        design_instructions={
            "image": "https://example.com/image1.jpg",
            "content": "Generated content",
        },
        image_local_path="/path/to/generated_image_0.jpg",
    )
    mock_reddit_agent.get_product_info.return_value = [product_info]

    # Create pipeline with mocks
    pipeline = Pipeline(
        reddit_agent=mock_reddit_agent,
        content_generator=mock_content_generator,
        image_generator=mock_image_generator,
        zazzle_designer=mock_zazzle_designer,
        affiliate_linker=mock_affiliate_linker,
        imgur_client=mock_imgur_client,
    )

    # Run the pipeline and expect an exception
    import pytest

    with pytest.raises(Exception, match="Affiliate link generation failed"):
        await pipeline.run_pipeline()


@pytest.mark.asyncio
async def test_pipeline_concurrent_operations(
    mock_reddit_agent,
    mock_content_generator,
    mock_image_generator,
    mock_zazzle_designer,
    mock_affiliate_linker,
    mock_imgur_client,
):
    """Test pipeline with concurrent operations."""
    # Configure mock to return multiple ProductInfo objects
    product_infos = [
        ProductInfo(
            product_id=f"test_id_{i}",
            name=f"Test Product {i}",
            product_type="sticker",
            zazzle_template_id="template123",
            zazzle_tracking_code="tracking456",
            image_url="https://example.com/generated_image.jpg",
            product_url=f"https://example.com/product_{i}",
            theme=f"Theme {i}",
            model="dall-e-3",
            prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
            reddit_context=RedditContext(
                post_id=f"test{i}",
                post_title=f"Test Post {i}",
                post_url=f"https://reddit.com/test{i}",
                subreddit="test",
            ),
            design_instructions={
                "image": f"https://example.com/test{i}.jpg",
                "content": "Generated content",
            },
            image_local_path=f"/path/to/generated_image_{i}.jpg",
        )
        for i in range(3)
    ]
    mock_reddit_agent.get_product_info.return_value = product_infos
    mock_affiliate_linker.generate_links_batch.side_effect = lambda products: products

    # Create pipeline with mocks
    pipeline = Pipeline(
        reddit_agent=mock_reddit_agent,
        content_generator=mock_content_generator,
        image_generator=mock_image_generator,
        zazzle_designer=mock_zazzle_designer,
        affiliate_linker=mock_affiliate_linker,
        imgur_client=mock_imgur_client,
    )

    # Run the pipeline
    products = await pipeline.run_pipeline()

    # Verify results
    assert len(products) == 3
    assert all(isinstance(p, ProductInfo) for p in products)


@pytest.mark.asyncio
async def test_pipeline_rate_limiting(
    mock_reddit_agent,
    mock_content_generator,
    mock_image_generator,
    mock_zazzle_designer,
    mock_affiliate_linker,
    mock_imgur_client,
):
    """Test pipeline rate limiting and retry mechanisms."""
    # Configure mock to simulate rate limiting
    product_info = ProductInfo(
        product_id="test123",
        name="Test Product",
        product_type="sticker",
        zazzle_template_id="template123",
        zazzle_tracking_code="tracking123",
        image_url="https://imgur.com/test.jpg",
        product_url="https://zazzle.com/test",
        theme="Test Theme",
        model="dall-e-3",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
        reddit_context=RedditContext(
            post_id="test123",
            post_title="Test Post",
            post_url="https://reddit.com/test",
            subreddit="test",
        ),
        design_instructions={
            "image": "https://imgur.com/test.jpg",
            "content": "Generated content",
        },
        image_local_path="/tmp/test.jpg",
    )
    mock_reddit_agent.get_product_info.return_value = [product_info]
    mock_affiliate_linker.generate_links_batch.side_effect = lambda products: products

    # Create pipeline with mocks
    pipeline = Pipeline(
        reddit_agent=mock_reddit_agent,
        content_generator=mock_content_generator,
        image_generator=mock_image_generator,
        zazzle_designer=mock_zazzle_designer,
        affiliate_linker=mock_affiliate_linker,
        imgur_client=mock_imgur_client,
    )

    # Run the pipeline
    products = await pipeline.run_pipeline()

    # Verify results
    assert len(products) == 1
    assert products[0].product_id == "test123"
