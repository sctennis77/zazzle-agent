import pytest
from unittest.mock import Mock, patch
from app.distribution.base import DistributionChannel
from app.distribution.reddit import RedditDistributionChannel, RedditDistributionError
from app.models import ProductInfo, RedditContext, DistributionStatus, DistributionMetadata
import os

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

class TestDistributionChannel:
    def test_abstract_methods(self):
        """Test that DistributionChannel is an abstract base class"""
        with pytest.raises(TypeError):
            DistributionChannel()

    def test_subclass_implementation(self):
        """Test that subclasses must implement required methods"""
        class IncompleteChannel(DistributionChannel):
            pass

        with pytest.raises(TypeError):
            IncompleteChannel()

class TestRedditDistributionChannel:
    @patch('os.getenv')
    def test_initialization(self, mock_getenv):
        """Test RedditDistributionChannel initialization"""
        mock_getenv.return_value = "test_value"
        channel = RedditDistributionChannel()
        assert isinstance(channel, DistributionChannel)

    @patch('os.getenv')
    def test_publish(self, mock_getenv, mock_product):
        """Test publishing a product to Reddit"""
        mock_getenv.return_value = "test_value"
        channel = RedditDistributionChannel()
        
        metadata = channel.publish(mock_product)
        assert metadata is not None
        assert metadata.status == DistributionStatus.PUBLISHED
        assert metadata.channel == "reddit"
        assert metadata.channel_url is not None

    @patch('os.getenv')
    def test_get_publication_url(self, mock_getenv, mock_product):
        """Test getting the publication URL"""
        mock_getenv.return_value = "test_value"
        channel = RedditDistributionChannel()
        
        url = channel.get_publication_url(mock_product)
        assert url is not None
        assert isinstance(url, str)
        assert url.startswith("https://reddit.com")

    @patch('os.getenv')
    def test_create_metadata(self, mock_getenv, mock_product):
        """Test creating distribution metadata."""
        mock_getenv.return_value = "test_value"
        channel = RedditDistributionChannel()
        # Test successful metadata (only status and error_message are supported)
        metadata = channel._create_metadata(DistributionStatus.PUBLISHED)
        assert metadata.status == DistributionStatus.PUBLISHED
        assert metadata.channel == "reddit"
        # Test error metadata
        metadata = channel._create_metadata(DistributionStatus.FAILED, error_message="Test error")
        assert metadata.status == DistributionStatus.FAILED
        assert metadata.error_message == "Test error" 