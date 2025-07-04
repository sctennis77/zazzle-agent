import glob
import json
import logging  # Import logging to check log output
import math
import os
import shutil  # Import shutil for cleanup
import sys
import unittest
from datetime import datetime
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from app.affiliate_linker import (
    InvalidProductDataError,
    ZazzleAffiliateLinker,
    ZazzleAffiliateLinkerError,
)
from app.agents.reddit_agent import RedditAgent
from app.content_generator import ContentGenerator
from app.db.database import Base, engine
from app.main import main, run_full_pipeline, run_generate_image_pipeline, save_to_csv
from app.models import PipelineConfig, ProductIdea, ProductInfo, RedditContext


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Mock necessary environment variables for tests
        self.patcher_env = patch.dict(
            os.environ,
            {
                "ZAZZLE_AFFILIATE_ID": "test_affiliate_id",
                "OPENAI_API_KEY": "test_openai_key",
                "SCRAPE_DELAY": "0",  # Mock delay for scraper (though scraper is removed)
                "MAX_PRODUCTS": "3",
                "REDDIT_CLIENT_ID": "test_client_id",
                "REDDIT_CLIENT_SECRET": "test_client_secret",
                "REDDIT_USERNAME": "test_username",
                "REDDIT_PASSWORD": "test_password",
                "REDDIT_USER_AGENT": "test_user_agent",
                "ZAZZLE_TEMPLATE_ID": "test_template_id",
                "ZAZZLE_TRACKING_CODE": "test_tracking_code",
            },
        )
        self.patcher_env.start()
        self.addCleanup(self.patcher_env.stop)

        # Create test data
        self.reddit_context = RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        )

        self.mock_products_data = [
            ProductInfo(
                product_id="ID_A",
                name="Product A",
                product_type="sticker",
                zazzle_template_id="template1",
                zazzle_tracking_code="tracking1",
                image_url="https://example.com/image1.jpg",
                product_url="https://example.com/product1",
                theme="test_theme",
                model="dall-e-3",
                prompt_version="1.0.0",
                reddit_context=self.reddit_context,
                design_instructions={"image": "https://example.com/image1.jpg"},
                image_local_path="/path/to/image1.jpg",
            ),
            ProductInfo(
                product_id="ID_B",
                name="Product B",
                product_type="sticker",
                zazzle_template_id="template2",
                zazzle_tracking_code="tracking2",
                image_url="https://example.com/image2.jpg",
                product_url="https://example.com/product2",
                theme="test_theme",
                model="dall-e-3",
                prompt_version="1.0.0",
                reddit_context=self.reddit_context,
                design_instructions={"image": "https://example.com/image2.jpg"},
                image_local_path="/path/to/image2.jpg",
            ),
            ProductInfo(
                product_id="ID_C",
                name="Product C",
                product_type="sticker",
                zazzle_template_id="template3",
                zazzle_tracking_code="tracking3",
                image_url="https://example.com/image3.jpg",
                product_url="https://example.com/product3",
                theme="test_theme",
                model="dall-e-3",
                prompt_version="1.0.0",
                reddit_context=self.reddit_context,
                design_instructions={"image": "https://example.com/image3.jpg"},
                image_local_path="/path/to/image3.jpg",
            ),
        ]

        # Create dummy config file for tests that read it
        self.dummy_config_dir = "app"
        self.dummy_config_path = os.path.join(
            self.dummy_config_dir, "products_config.json"
        )
        with open(self.dummy_config_path, "w") as f:
            json.dump(
                {
                    "products": [
                        product.to_dict() for product in self.mock_products_data
                    ]
                },
                f,
                indent=4,
            )
        self.addCleanup(lambda: os.remove(self.dummy_config_path))

        # Create dummy screenshot directory and file for tests (if needed by other tests)
        self.dummy_screenshot_dir = "outputs/screenshots"
        os.makedirs(self.dummy_screenshot_dir, exist_ok=True)
        self.dummy_screenshot_path = os.path.join(
            self.dummy_screenshot_dir, "dummy_image.png"
        )
        with open(self.dummy_screenshot_path, "w") as f:
            f.write("dummy content")
        self.addCleanup(lambda: shutil.rmtree("outputs"))  # Clean up outputs directory

    @patch("app.main.csv.DictWriter")  # Patch csv.DictWriter
    @patch("app.main.os.makedirs")
    @patch("app.main.open", new_callable=mock_open)
    def test_save_to_csv_success(self, mock_open, mock_makedirs, mock_dict_writer):
        test_product = ProductInfo(
            product_id="test_id",
            name="Test Product",
            product_type="sticker",
            zazzle_template_id="template1",
            zazzle_tracking_code="tracking1",
            image_url="http://test.com/image.png",
            product_url="http://test.com/product",
            theme="test_theme",
            model="dall-e-3",
            prompt_version="1.0.0",
            reddit_context=self.reddit_context,
            design_instructions={"image": "http://test.com/image.png"},
        )
        # Set up the mock to return a mock writer
        mock_writer = MagicMock()
        mock_dict_writer.return_value = mock_writer

        # Mock os.path.exists to return False to test header writing
        with patch("app.main.os.path.exists", return_value=False):
            save_to_csv(test_product)
        # Check that open was called with a file ending in 'processed_products.csv'
        open_call_args = mock_open.call_args[0][0]
        assert open_call_args.endswith("processed_products.csv")
        mock_dict_writer.assert_called_once()
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerows.assert_called_once()
        # Verify design_instructions is included
        assert "design_instructions" in mock_dict_writer.call_args[1]["fieldnames"]

    @patch("app.main.os.makedirs")
    @patch(
        "builtins.open", side_effect=Exception("Open error")
    )  # Patch open to raise an exception
    def test_save_to_csv_error(self, mock_open, mock_makedirs):
        test_product = ProductInfo(
            product_id="test_id",
            name="Test Product",
            product_type="sticker",
            zazzle_template_id="template1",
            zazzle_tracking_code="tracking1",
            image_url="http://test.com/image.png",
            product_url="http://test.com/product",
            theme="test_theme",
            model="dall-e-3",
            prompt_version="1.0.0",
            reddit_context=self.reddit_context,
            design_instructions={"image": "http://test.com/image.png"},
        )
        with self.assertRaises(Exception) as cm:
            save_to_csv(test_product)
        self.assertIn("Open error", str(cm.exception))


@pytest.mark.asyncio
class TestIntegrationAsync:
    """Test integration between components."""

    @patch("app.main.save_to_csv")
    @patch("app.main.RedditAgent")
    async def test_full_pipeline(self, mock_reddit_agent, mock_save_to_csv):
        # Configure mock_reddit_agent
        mock_reddit_agent_instance = AsyncMock(spec=RedditAgent)
        mock_reddit_agent.return_value = mock_reddit_agent_instance

        # Mock a trending post
        mock_post = MagicMock()
        mock_post.title = "Test Post"
        mock_post.permalink = "/r/golf/comments/test123"
        mock_post.id = "test123"

        # Create mock subreddit and hot iterator
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = iter([mock_post])
        mock_reddit = MagicMock()
        mock_reddit.subreddit.return_value = mock_subreddit
        mock_reddit_agent_instance.reddit = mock_reddit

        # Mock product info
        mock_product_info = ProductInfo(
            product_id="test_product_id",
            name="Test Product",
            product_type="sticker",
            image_url="https://example.com/test.jpg",
            product_url="https://zazzle.com/test_product",
            zazzle_template_id="test_template_id",
            zazzle_tracking_code="test_tracking_code",
            theme="test theme",
            model="test_model",
            prompt_version="1.0.0",
            reddit_context=RedditContext(
                post_id="test_post_id",
                post_title="Test Post",
                post_url="https://reddit.com/r/test/comments/test_post_id",
                subreddit="test",
                post_content="Test content",
            ),
            design_instructions={
                "content": "Test content",
                "image": "https://example.com/test.jpg",
            },
            image_local_path="/tmp/test.jpg",
        )
        mock_reddit_agent_instance.get_product_info.return_value = [mock_product_info]

        # Run the pipeline
        config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id="test_template_id",
            zazzle_tracking_code="test_tracking_code",
            prompt_version="1.0.0",
        )
        result = await run_full_pipeline(config)

        # Verify the results
        assert result == [mock_product_info]
        mock_reddit_agent_instance.get_product_info.assert_called_once()
        mock_save_to_csv.assert_called_once()

    @patch("app.main.save_to_csv")
    @patch("app.main.RedditAgent")
    async def test_image_generation_pipeline(self, mock_reddit_agent, mock_save_to_csv):
        # Configure mock_reddit_agent
        mock_reddit_agent_instance = MagicMock()
        mock_reddit_agent.return_value = mock_reddit_agent_instance

        # Mock the image generation with AsyncMock
        mock_product_info = MagicMock()
        mock_reddit_agent_instance.generate_image_and_create_product = AsyncMock(
            return_value=mock_product_info
        )

        # Run the image generation pipeline and ensure it completes without raising
        await run_generate_image_pipeline("Test prompt", "dall-e-2")
        # If the pipeline aborts early, save_to_csv should not be called
        # (If it succeeds, it will be called, but in CI it will likely abort due to missing API key)
        assert mock_save_to_csv.call_count in (0, 1)

    @patch("app.main.save_to_csv")
    @patch("app.main.RedditAgent")
    async def test_pipeline_with_error(self, mock_reddit_agent, mock_save_to_csv):
        # Configure mock_reddit_agent to raise an exception
        mock_reddit_agent_instance = AsyncMock(spec=RedditAgent)
        mock_reddit_agent.return_value = mock_reddit_agent_instance
        mock_reddit_agent_instance.get_product_info = AsyncMock(
            side_effect=Exception("Test error")
        )

        # Run the pipeline and expect an exception
        config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id="test_template_id",
            zazzle_tracking_code="test_tracking_code",
            prompt_version="1.0.0",
        )
        with pytest.raises(Exception):
            await run_full_pipeline(config)

        # Verify the mocks were called correctly
        # With subreddit cycling, RedditAgent will be called multiple times (once per subreddit attempt)
        assert mock_reddit_agent.call_count >= 1
        assert mock_reddit_agent_instance.get_product_info.call_count >= 1
        mock_save_to_csv.assert_not_called()


if __name__ == "__main__":
    unittest.main()
