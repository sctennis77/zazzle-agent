import csv
import json
import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.agents.reddit_agent import RedditAgent
from app.db.database import Base, SessionLocal, engine
from app.image_generator import ImageGenerator
from app.main import run_full_pipeline
from app.models import (
    DesignInstructions,
    PipelineConfig,
    ProductIdea,
    ProductInfo,
    RedditContext,
)
from app.zazzle_product_designer import ZazzleProductDesigner


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Drop and recreate all tables before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def patch_openai():
    with (
        patch("app.image_generator.OpenAI") as mock_img,
        patch("app.content_generator.OpenAI") as mock_content,
        patch("app.agents.reddit_agent.openai.OpenAI") as mock_reddit,
    ):
        mock_instance = MagicMock()
        mock_img.return_value = mock_instance
        mock_content.return_value = mock_instance
        mock_reddit.return_value = mock_instance
        mock_instance.images.generate.return_value = MagicMock(
            data=[MagicMock(b64_json="Zm9vYmFy")]
        )
        mock_instance.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"text": "Test Text", "image_description": "A fun cartoon golf ball with sunglasses.", "theme": "test_theme", "color": "Blue", "quantity": 1}'
                    )
                )
            ]
        )
        yield mock_instance


@pytest.fixture
def mock_openai():
    with patch("app.image_generator.OpenAI") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        # Mock image generation response
        mock_instance.images.generate.return_value = MagicMock(
            data=[MagicMock(b64_json="Zm9vYmFy")]
        )
        # Mock chat completion response with all required fields for product idea
        product_idea_json = '{"text": "Test Text", "image_description": "A fun cartoon golf ball with sunglasses.", "theme": "test_theme", "color": "Blue", "quantity": 1}'
        mock_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=product_idea_json))]
        )
        yield mock_instance


@pytest.fixture
def mock_reddit():
    with patch("praw.Reddit") as mock:
        reddit = MagicMock()
        mock.return_value = reddit
        
        # Mock subreddit metadata
        subreddit_mock = MagicMock()
        subreddit_mock.id = "test_subreddit_id"
        subreddit_mock.name = "test_subreddit"
        subreddit_mock.display_name = "test_subreddit"
        subreddit_mock.description = "Test subreddit description"
        subreddit_mock.description_html = "<p>Test subreddit description</p>"
        subreddit_mock.public_description = "Test public description"
        subreddit_mock.created_utc = 1234567890.0
        subreddit_mock.subscribers = 1000
        subreddit_mock.over18 = False
        subreddit_mock.spoilers_enabled = False
        
        # Mock post
        post = MagicMock()
        post.id = "test_post_id"
        post.title = "Test Post"
        post.selftext = "Test content"
        post.url = "https://reddit.com/r/test/test_post_id"
        post.permalink = "/r/test/test_post_id"
        post.subreddit = subreddit_mock
        
        # Mock comment
        comment = MagicMock()
        comment.id = "test_comment_id"
        comment.body = "Test comment"
        
        # Mock comments as a CommentForest-like object
        comments_mock = MagicMock()
        comments_mock.replace_more.return_value = None
        comments_mock.__iter__.return_value = iter([comment])
        post.comments = comments_mock
        
        reddit.subreddit.return_value = subreddit_mock
        subreddit_mock.hot.return_value = iter([post])
        
        yield reddit


@pytest.fixture
def mock_imgur():
    with patch("app.clients.imgur_client.ImgurClient") as mock:
        client = MagicMock()
        mock.return_value = client
        # Mock upload_image to return both URL and local path
        client.upload_image.return_value = (
            "https://i.imgur.com/test.png",
            "/tmp/test_image.png",
        )
        yield client


@pytest.fixture
def mock_zazzle():
    with patch("app.zazzle_product_designer.ZazzleProductDesigner") as mock:
        designer = MagicMock()

        def create_product_side_effect(design_instructions):
            reddit_context = RedditContext(
                post_id="test_post_id",
                post_title="Test Post Title",
                post_url="https://reddit.com/test",
                subreddit="test_subreddit",
            )

            return ProductInfo(
                product_id="test_product_id",
                name=design_instructions.get("name", "Test Product"),
                image_url=design_instructions.get(
                    "image", "https://i.imgur.com/test.png"
                ),
                product_url="https://www.zazzle.com/test_product",
                theme="test_theme",
                product_type=design_instructions.get("product_type", "sticker"),
                zazzle_template_id=design_instructions.get(
                    "zazzle_template_id", "test_template"
                ),
                zazzle_tracking_code=design_instructions.get(
                    "zazzle_tracking_code", "test_tracking"
                ),
                model="dall-e-3",
                prompt_version="1.0.0",
                reddit_context=reddit_context,
                design_instructions=design_instructions,
                image_local_path="/path/to/test_image.png",
            )

        designer.create_product.side_effect = create_product_side_effect
        mock.return_value = designer
        yield designer


@pytest.fixture(autouse=True)
def mock_image_generator():
    with patch.object(ImageGenerator, "generate_image", new_callable=AsyncMock) as mock:
        mock.return_value = ("https://i.imgur.com/test.png", "/tmp/test_image.png")
        yield mock


@pytest.fixture
def mock_zazzle_response():
    return {
        "product_id": "test123",
        "product_url": "https://zazzle.com/test123",
        "tracking_code": "track123",
    }


@pytest.fixture
def mock_product():
    reddit_context = RedditContext(
        post_id="test_post_id",
        post_title="Test Post Title",
        post_url="https://reddit.com/test",
        subreddit="test_subreddit",
    )

    return ProductInfo(
        product_id="test123",
        name="Test Product",
        image_url="https://example.com/image.jpg",
        product_url="https://zazzle.com/test123",
        theme="test",
        product_type="sticker",
        zazzle_template_id="template123",
        zazzle_tracking_code="track123",
        model="dall-e-2",
        prompt_version="1.0",
        reddit_context=reddit_context,
        design_instructions={"image": "https://example.com/image.jpg"},
        image_local_path="/path/to/test_image.png",
    )


@pytest.mark.asyncio
async def test_end_to_end_pipeline_with_csv_output(
    mock_openai, mock_reddit, mock_imgur, mock_zazzle, mock_image_generator, tmp_path
):
    """Test the full pipeline with CSV output."""
    # Set up test environment
    os.environ["OPENAI_API_KEY"] = "test_key"
    os.environ["ZAZZLE_AFFILIATE_ID"] = "test_affiliate"
    os.environ["ZAZZLE_TEMPLATE_ID"] = "test_template"
    os.environ["ZAZZLE_TRACKING_CODE"] = "test_tracking"
    os.environ["IMGUR_CLIENT_ID"] = "test_client_id"
    os.environ["IMGUR_CLIENT_SECRET"] = "test_client_secret"

    # Create test output directory
    test_output_dir = tmp_path / "test_outputs"
    test_output_dir.mkdir()
    os.environ["OUTPUT_DIR"] = str(test_output_dir)

    # Create a test product
    test_product = ProductInfo(
        product_id="test123",
        name="Test Product",
        product_type="sticker",
        image_url="https://example.com/image.jpg",
        product_url="https://zazzle.com/test123",
        zazzle_template_id="test_template",
        zazzle_tracking_code="test_tracking",
        theme="test_theme",
        model="dall-e-3",
        prompt_version="1.0.0",
        reddit_context=RedditContext(
            post_id="test_post",
            post_title="Test Post",
            post_url="https://reddit.com/test_post",
            subreddit="test_subreddit",
        ),
        design_instructions={"image": "https://example.com/image.jpg"},
    )

    # Mock the RedditAgent to return our test product
    with (
        patch("app.main.RedditAgent") as mock_reddit_agent_class,
        patch("app.agents.reddit_agent.RedditAgent") as mock_reddit_agent_impl,
    ):
        mock_agent = AsyncMock(spec=RedditAgent)
        mock_agent.get_product_info = AsyncMock(return_value=[test_product])

        # Create mock subreddit and hot iterator
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = iter([])
        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit
        mock_agent.reddit = mock_reddit

        mock_reddit_agent_class.return_value = mock_agent
        mock_reddit_agent_impl.return_value = mock_agent

        # Run the pipeline
        config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id="test_template",
            zazzle_tracking_code="test_tracking",
            prompt_version="1.0.0",
        )
        result = await run_full_pipeline(config)
        assert result == [test_product]


@pytest.mark.asyncio
async def test_end_to_end_pipeline_with_different_model(
    mock_openai, mock_reddit, mock_imgur, mock_zazzle, mock_image_generator, tmp_path
):
    """Test the full pipeline with a different model."""
    # Set up test environment
    os.environ["OPENAI_API_KEY"] = "test_key"
    os.environ["ZAZZLE_AFFILIATE_ID"] = "test_affiliate"
    os.environ["ZAZZLE_TEMPLATE_ID"] = "test_template"
    os.environ["ZAZZLE_TRACKING_CODE"] = "test_tracking"
    os.environ["IMGUR_CLIENT_ID"] = "test_client_id"
    os.environ["IMGUR_CLIENT_SECRET"] = "test_client_secret"

    # Create test output directory
    test_output_dir = tmp_path / "test_outputs"
    test_output_dir.mkdir()
    os.environ["OUTPUT_DIR"] = str(test_output_dir)

    # Create a test product
    test_product = ProductInfo(
        product_id="test123",
        name="Test Product",
        product_type="sticker",
        image_url="https://example.com/image.jpg",
        product_url="https://zazzle.com/test123",
        zazzle_template_id="test_template",
        zazzle_tracking_code="test_tracking",
        theme="test_theme",
        model="dall-e-2",
        prompt_version="1.0.0",
        reddit_context=RedditContext(
            post_id="test_post",
            post_title="Test Post",
            post_url="https://reddit.com/test_post",
            subreddit="test_subreddit",
        ),
        design_instructions={"image": "https://example.com/image.jpg"},
    )

    # Mock the RedditAgent to return our test product
    with (
        patch("app.main.RedditAgent") as mock_reddit_agent_class,
        patch("app.agents.reddit_agent.RedditAgent") as mock_reddit_agent_impl,
    ):
        mock_agent = AsyncMock(spec=RedditAgent)
        mock_agent.get_product_info = AsyncMock(return_value=[test_product])

        # Create mock subreddit and hot iterator
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = iter([])
        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit
        mock_agent.reddit = mock_reddit

        mock_reddit_agent_class.return_value = mock_agent
        mock_reddit_agent_impl.return_value = mock_agent

        # Run the pipeline with DALL-E 2
        config = PipelineConfig(
            model="dall-e-2",
            zazzle_template_id="test_template",
            zazzle_tracking_code="test_tracking",
            prompt_version="1.0.0",
        )
        result = await run_full_pipeline(config)
        assert result == [test_product]


@pytest.mark.asyncio
async def test_create_product_success(mock_zazzle_response):
    """Test successful product creation."""
    # Mock session and post
    session = Mock()
    mock_response = Mock()
    mock_response.status = 200

    async def mock_json():
        return mock_zazzle_response

    mock_response.json = mock_json

    class MockCM:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, exc_type, exc, tb):
            return None

    def post(*args, **kwargs):
        return MockCM()

    session.post.side_effect = post

    designer = ZazzleProductDesigner(
        affiliate_id="test123", session=session, headers={}
    )

    # Create design instructions with template ID
    design_instructions = DesignInstructions(
        image="https://example.com/image.jpg",
        theme="test_theme",
        template_id="template123",
    )

    result = await designer.create_product(design_instructions)
    assert result is not None
    assert isinstance(result.product_id, str)
    assert result.product_id.startswith("prod_")
    assert result.product_url.startswith(
        "https://www.zazzle.com/api/create/at-test123?"
    )
    assert "pd=template123" in result.product_url
    assert "t_image1_url=https%3A//example.com/image.jpg" in result.product_url
    assert "tc=Clouvel-0" in result.product_url


@pytest.mark.asyncio
async def test_create_product_failure():
    """Test product creation failure."""
    # Mock session and post
    session = Mock()
    mock_response = Mock()
    mock_response.status = 400

    async def mock_json():
        return {}

    mock_response.json = mock_json

    class MockCM:
        async def __aenter__(self):
            return mock_response

        async def __aexit__(self, exc_type, exc, tb):
            return None

    def post(*args, **kwargs):
        return MockCM()

    session.post.side_effect = post

    designer = ZazzleProductDesigner(
        affiliate_id="test123", session=session, headers={}
    )

    # Create design instructions with template ID
    design_instructions = DesignInstructions(
        image=None, theme="test_theme", template_id="template123"
    )

    result = await designer.create_product(design_instructions)
    assert result is None


@pytest.mark.asyncio
async def test_create_product_missing_required():
    """Test product creation with missing required fields."""
    designer = ZazzleProductDesigner(affiliate_id="test123", session=Mock(), headers={})

    # Create design instructions with missing required fields
    design_instructions = DesignInstructions(
        image=None, theme="test_theme", template_id="template123"
    )

    result = await designer.create_product(design_instructions)
    assert result is None
