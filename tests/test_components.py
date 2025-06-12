import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.affiliate_linker import ZazzleAffiliateLinker
from app.content_generator import ContentGenerator
from app.models import ProductInfo, RedditContext, ProductIdea, PipelineConfig
import logging
from datetime import datetime
import json
import glob
import shutil
from io import StringIO
import sys

@pytest.fixture(autouse=True)
def setup():
    # Mock necessary environment variables for tests
    with patch.dict(os.environ, {
        'ZAZZLE_AFFILIATE_ID': 'test_affiliate_id',
        'OPENAI_API_KEY': 'test_openai_key',
        'ZAZZLE_TEMPLATE_ID': 'test_template_id',
        'ZAZZLE_TRACKING_CODE': 'test_tracking_code'
    }):
        yield

@pytest.fixture
def reddit_context():
    return RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit'
    )

@pytest.fixture
def mock_product_info(reddit_context):
    return ProductInfo(
        product_id="test_product_id",
        name="Test Product",
        product_type="sticker",
        zazzle_template_id="test_template_id",
        zazzle_tracking_code="test_tracking_code",
        image_url="https://example.com/image.jpg",
        product_url="https://example.com/product",
        theme="test_theme",
        model="dall-e-3",
        prompt_version="1.0.0",
        reddit_context=reddit_context,
        design_instructions={"image": "https://example.com/image.jpg"},
        image_local_path="/path/to/image.jpg"
    )

@pytest.fixture
def mock_product_idea(reddit_context):
    return ProductIdea(
        theme="Test Theme",
        image_description="Test image description",
        design_instructions={"image": "https://example.com/image.jpg"},
        reddit_context=reddit_context,
        model="dall-e-3",
        prompt_version="1.0.0"
    )

@pytest.mark.asyncio
class TestComponents:
    @pytest.fixture
    def affiliate_linker(self):
        return ZazzleAffiliateLinker(
            zazzle_affiliate_id='test_affiliate_id',
            zazzle_tracking_code='test_tracking_code'
        )

    @pytest.fixture
    def content_generator(self):
        return ContentGenerator()

    async def test_affiliate_linker(self, affiliate_linker, mock_product_info):
        # Mock the _generate_affiliate_link method
        affiliate_linker._generate_affiliate_link = AsyncMock(return_value="https://www.zazzle.com/product/test_product_id?rf=test_affiliate_id")
        
        # Test generating links for a product
        result = await affiliate_linker.generate_links_batch([mock_product_info])
        
        # Verify the result
        assert len(result) == 1
        assert result[0].affiliate_link == "https://www.zazzle.com/product/test_product_id?rf=test_affiliate_id"
        assert result[0].product_id == mock_product_info.product_id

    def test_content_generator(self, content_generator, mock_product_idea):
        # Mock the OpenAI API call
        with patch.object(content_generator.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps({
                    "product_id": "test_product_id",
                    "name": "Test Product",
                    "product_type": "sticker",
                    "theme": "test_theme",
                    "design_instructions": {"image": "https://example.com/image.jpg"}
                })))]
            )
            
            # Test generating content
            result = content_generator.generate_content(mock_product_idea.theme)
            
            # Verify the result
            assert isinstance(result, str)
            assert "Test Product" in result or "test_product_id" in result

    def test_content_generator_error(self, content_generator, mock_product_idea):
        # Mock the OpenAI API call to raise an error
        with patch.object(content_generator.client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            # Test error handling
            result = content_generator.generate_content(mock_product_idea.theme)
            assert result == "Error generating content"

    def test_content_generator_empty(self, content_generator):
        # Test with empty product ideas list
        result = content_generator.generate_content("")
        assert isinstance(result, str)

    def test_content_generator_invalid_response(self, content_generator, mock_product_idea):
        # Mock the OpenAI API call to return invalid JSON
        with patch.object(content_generator.client.chat.completions, 'create') as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="invalid json"))]
            )
            
            # Test error handling
            result = content_generator.generate_content(mock_product_idea.theme)
            assert result == "Error generating content" 