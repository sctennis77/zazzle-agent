import pytest

from app.async_image_generator import IMAGE_GENERATION_BASE_PROMPTS
from app.models import AffiliateLinker, PipelineConfig, ProductIdea, RedditContext


def test_pipeline_config():
    """Test PipelineConfig creation and logging."""
    config = PipelineConfig(
        model="dall-e-3",
        zazzle_template_id="template123",
        zazzle_tracking_code="tracking456",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
    )

    assert config.model == "dall-e-3"
    assert config.zazzle_template_id == "template123"
    assert config.zazzle_tracking_code == "tracking456"
    assert config.prompt_version == IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"]


def test_reddit_context():
    """Test RedditContext creation and logging."""
    context = RedditContext(
        post_id="test_post_id",
        post_title="Test Post Title",
        post_url="https://reddit.com/test",
        subreddit="test_subreddit",
        post_content="Test post content",
        comments=[{"id": "comment1", "text": "Test comment"}],
    )

    assert context.post_id == "test_post_id"
    assert context.post_title == "Test Post Title"
    assert context.post_url == "https://reddit.com/test"
    assert context.subreddit == "test_subreddit"
    assert context.post_content == "Test post content"
    assert len(context.comments) == 1


def test_product_idea():
    """Test ProductIdea creation and logging."""
    reddit_context = RedditContext(
        post_id="test_post_id",
        post_title="Test Post Title",
        post_url="https://reddit.com/test",
        subreddit="test_subreddit",
    )

    idea = ProductIdea(
        theme="test_theme",
        image_description="Test image description",
        design_instructions={"image": "https://example.com/image.jpg"},
        reddit_context=reddit_context,
        model="dall-e-3",
        prompt_version=IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"],
    )

    assert idea.theme == "test_theme"
    assert idea.image_description == "Test image description"
    assert idea.design_instructions["image"] == "https://example.com/image.jpg"
    assert idea.model == "dall-e-3"
    assert idea.prompt_version == IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["version"]
    assert idea.reddit_context == reddit_context


def test_affiliate_linker():
    linker = AffiliateLinker(
        zazzle_affiliate_id="test_affiliate_id",
        zazzle_tracking_code="test_tracking_code",
    )
    product_url = "https://example.com/product"
    expected_link = f"{product_url}?rf=test_affiliate_id&tc=test_tracking_code"
    assert linker.compose_affiliate_link(product_url) == expected_link
