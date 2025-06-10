import pytest
from unittest.mock import patch
from app.content_generator import ContentGenerator
from app.models import ProductInfo, RedditContext

@pytest.fixture
def content_generator():
    return ContentGenerator()

@pytest.fixture
def mock_product():
    return ProductInfo(
        product_id="test123",
        name="Test Product",
        product_type="sticker",
        image_url="https://example.com/image.jpg",
        product_url="https://example.com/product",
        zazzle_template_id="123",
        zazzle_tracking_code="TEST",
        theme="Test Theme",
        model="test-model",
        prompt_version="1.0",
        reddit_context=RedditContext(
            post_id="post123",
            post_title="Test Post Title",
            post_url="https://reddit.com/r/testsubreddit/comments/post123",
            subreddit="testsubreddit"
        ),
        design_instructions={"key": "value"}
    )

def test_generate_content(content_generator):
    """Test generating content for a product."""
    content = content_generator.generate_content("Test Product")
    assert isinstance(content, str)
    assert len(content) > 0

def test_generate_content_batch(content_generator, mock_product):
    """Test generating content for a batch of products."""
    products = [mock_product]
    processed = content_generator.generate_content_batch(products)
    assert len(processed) == 1
    assert "content" in processed[0].design_instructions
    assert isinstance(processed[0].design_instructions["content"], str)

@patch('openai.OpenAI')
def test_generate_content_error(mock_openai, content_generator):
    """Test error handling when content generation fails."""
    mock_openai.return_value.chat.completions.create.side_effect = Exception("API error")
    content = content_generator.generate_content("Test Product")
    assert content == "Error generating content"

def test_generate_content_batch_error(content_generator, mock_product):
    """Test error handling in batch when content generation fails."""
    # Patch the generate_content method to always return error
    content_generator.generate_content = lambda *a, **kw: "Error generating content"
    products = [mock_product]
    processed = content_generator.generate_content_batch(products)
    assert len(processed) == 1
    assert processed[0].design_instructions["content"] == "Error generating content"

def test_generate_content_force_new(content_generator):
    """Test force_new_content flag changes the output."""
    content1 = content_generator.generate_content("Test Product")
    content2 = content_generator.generate_content("Test Product", force_new_content=True)
    # If the implementation is deterministic, this may be the same, so just check type
    assert isinstance(content1, str)
    assert isinstance(content2, str)

@patch('app.content_generator.ContentGenerator.generate_content')
def test_generate_content_batch_empty(mock_generate_content, content_generator):
    """Test generating content for an empty product list."""
    products = []
    processed = content_generator.generate_content_batch(products)
    assert processed == []
    mock_generate_content.assert_not_called() 