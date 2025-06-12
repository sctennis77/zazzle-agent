import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.pipeline import Pipeline
from app.models import ProductIdea, RedditContext, ProductInfo, PipelineConfig
from app.db.models import PipelineRun, ErrorLog
from app.db.database import SessionLocal
from sqlalchemy.exc import SQLAlchemyError

@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.query = MagicMock()
    return session

@pytest.fixture
def pipeline(mock_session):
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
    content_generator.generate_content = AsyncMock(return_value="Test content")
    image_generator = MagicMock()
    image_generator.generate_image = AsyncMock(return_value=("https://imgur.com/test.jpg", "/tmp/test.jpg"))
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

@pytest.fixture
def sample_product_info():
    """Create a sample product info for testing."""
    reddit_context = RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit'
    )
    return ProductInfo(
        product_id='test_id',
        name='Test Product',
        product_type='t-shirt',
        image_url='https://imgur.com/test.jpg',
        product_url='https://zazzle.com/test',
        zazzle_template_id='template123',
        zazzle_tracking_code='tracking456',
        theme='test_theme',
        model='dall-e-3',
        prompt_version='1.0.0',
        reddit_context=reddit_context,
        design_instructions={'image': 'https://example.com/image.jpg', 'content': 'Test content'}
    )

@pytest.mark.asyncio
async def test_log_error(pipeline, mock_session):
    """Test logging an error to the database."""
    pipeline.pipeline_run_id = 1
    pipeline.session = mock_session
    error_message = "Test error message"
    pipeline.log_error(error_message)
    mock_session.add.assert_called_once()

@pytest.mark.asyncio
async def test_process_product_idea_error(pipeline, sample_product_idea):
    """Test handling of errors during product idea processing."""
    pipeline.content_generator.generate_content.side_effect = Exception("Content generation failed")
    with pytest.raises(Exception):
        await pipeline.process_product_idea(sample_product_idea)

@pytest.mark.asyncio
async def test_run_pipeline_error(pipeline, mock_session):
    """Test handling of errors during pipeline execution (should log error, not raise)."""
    pipeline.pipeline_run_id = 1
    pipeline.session = mock_session
    pipeline.reddit_agent.find_and_create_product.side_effect = Exception("Pipeline execution failed")
    # Should not raise, just log error and set status to failed
    await pipeline.run(1, mock_session)
    # Check that log_error was called (by checking mock_session.add was called)
    assert mock_session.add.called

@pytest.mark.asyncio
async def test_retry_logic(pipeline, sample_product_idea, sample_product_info):
    """Test retry logic for product creation."""
    pipeline.zazzle_designer.create_product.side_effect = [Exception("Retry error"), sample_product_info]
    pipeline.affiliate_linker.generate_links_batch.return_value = [sample_product_info]
    result = await pipeline.process_product_idea(sample_product_idea)
    assert result is not None
    assert pipeline.zazzle_designer.create_product.call_count == 2

@pytest.mark.asyncio
async def test_database_persistence_error(pipeline, sample_product_idea, mock_session):
    """Test handling of database persistence errors (should raise if error logging also fails)."""
    pipeline.pipeline_run_id = 1
    pipeline.session = mock_session
    pipeline.affiliate_linker.generate_links_batch.return_value = []
    # Both add calls raise
    mock_session.add.side_effect = SQLAlchemyError("Database error")
    with pytest.raises(SQLAlchemyError):
        await pipeline.process_product_idea(sample_product_idea)

@pytest.mark.asyncio
async def test_missing_pipeline_run_id(pipeline, sample_product_idea, sample_product_info):
    """Test handling of missing pipeline_run_id."""
    pipeline.pipeline_run_id = None
    pipeline.affiliate_linker.generate_links_batch.return_value = [sample_product_info]
    result = await pipeline.process_product_idea(sample_product_idea)
    assert result is not None

@pytest.mark.asyncio
async def test_missing_session(pipeline, sample_product_idea, sample_product_info):
    """Test handling of missing session."""
    pipeline.session = None
    pipeline.affiliate_linker.generate_links_batch.return_value = [sample_product_info]
    result = await pipeline.process_product_idea(sample_product_idea)
    assert result is not None 