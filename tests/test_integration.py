import os
import unittest
from unittest.mock import patch, MagicMock, mock_open, AsyncMock
import pandas as pd
import math
from app.main import main, save_to_csv, run_full_pipeline
from app.affiliate_linker import ZazzleAffiliateLinker, ZazzleAffiliateLinkerError, InvalidProductDataError
from app.content_generator import ContentGenerator
import logging # Import logging to check log output
from datetime import datetime
from app.models import ProductInfo, RedditContext, ProductIdea, PipelineConfig
import pytest
import json
import glob
import shutil # Import shutil for cleanup
from app.agents.reddit_agent import RedditAgent
from io import StringIO
import sys

class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Mock necessary environment variables for tests
        self.patcher_env = patch.dict(os.environ, {
            'ZAZZLE_AFFILIATE_ID': 'test_affiliate_id',
            'OPENAI_API_KEY': 'test_openai_key',
            'SCRAPE_DELAY': '0', # Mock delay for scraper (though scraper is removed)
            'MAX_PRODUCTS': '3',
            'REDDIT_CLIENT_ID': 'test_client_id',
            'REDDIT_CLIENT_SECRET': 'test_client_secret',
            'REDDIT_USERNAME': 'test_username',
            'REDDIT_PASSWORD': 'test_password',
            'REDDIT_USER_AGENT': 'test_user_agent',
            'ZAZZLE_TEMPLATE_ID': 'test_template_id',
            'ZAZZLE_TRACKING_CODE': 'test_tracking_code'
        })
        self.patcher_env.start()
        self.addCleanup(self.patcher_env.stop)

        # Create test data
        self.reddit_context = RedditContext(
            post_id='test_post_id',
            post_title='Test Post Title',
            post_url='https://reddit.com/test',
            subreddit='test_subreddit'
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
                image_local_path="/path/to/image1.jpg"
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
                image_local_path="/path/to/image2.jpg"
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
                image_local_path="/path/to/image3.jpg"
            )
        ]

        # Create dummy config file for tests that read it
        self.dummy_config_dir = 'app'
        self.dummy_config_path = os.path.join(self.dummy_config_dir, 'products_config.json')
        with open(self.dummy_config_path, 'w') as f:
            json.dump({'products': [product.to_dict() for product in self.mock_products_data]}, f, indent=4)
        self.addCleanup(lambda: os.remove(self.dummy_config_path))

        # Create dummy screenshot directory and file for tests (if needed by other tests)
        self.dummy_screenshot_dir = 'outputs/screenshots'
        os.makedirs(self.dummy_screenshot_dir, exist_ok=True)
        self.dummy_screenshot_path = os.path.join(self.dummy_screenshot_dir, 'dummy_image.png')
        with open(self.dummy_screenshot_path, 'w') as f:
            f.write("dummy content")
        self.addCleanup(lambda: shutil.rmtree('outputs')) # Clean up outputs directory

    @patch('app.main.csv.DictWriter') # Patch csv.DictWriter
    @patch('app.main.os.makedirs')
    @patch('app.main.open', new_callable=mock_open)
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
            design_instructions={"image": "http://test.com/image.png"}
        )
        # Set up the mock to return a mock writer
        mock_writer = MagicMock()
        mock_dict_writer.return_value = mock_writer
        
        # Mock os.path.exists to return False to test header writing
        with patch('app.main.os.path.exists', return_value=False):
            save_to_csv(test_product)
        # Check that open was called with a file ending in 'processed_products.csv'
        open_call_args = mock_open.call_args[0][0]
        assert open_call_args.endswith('processed_products.csv')
        mock_dict_writer.assert_called_once()
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerows.assert_called_once()
        # Verify design_instructions is included
        assert 'design_instructions' in mock_dict_writer.call_args[1]['fieldnames']

    @patch('app.main.os.makedirs')
    @patch('builtins.open', side_effect=Exception("Open error")) # Patch open to raise an exception
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
            design_instructions={"image": "http://test.com/image.png"}
        )
        with self.assertRaises(Exception) as cm:
            save_to_csv(test_product)
        self.assertIn("Open error", str(cm.exception))

@pytest.mark.asyncio
class TestIntegrationAsync:
    @pytest.fixture(autouse=True)
    def setup(self):
        # Mock necessary environment variables for tests
        self.patcher_env = patch.dict(os.environ, {
            'ZAZZLE_AFFILIATE_ID': 'test_affiliate_id',
            'OPENAI_API_KEY': 'test_openai_key',
            'SCRAPE_DELAY': '0',
            'MAX_PRODUCTS': '3',
            'REDDIT_CLIENT_ID': 'test_client_id',
            'REDDIT_CLIENT_SECRET': 'test_client_secret',
            'REDDIT_USERNAME': 'test_username',
            'REDDIT_PASSWORD': 'test_password',
            'REDDIT_USER_AGENT': 'test_user_agent',
            'ZAZZLE_TEMPLATE_ID': 'test_template_id',
            'ZAZZLE_TRACKING_CODE': 'test_tracking_code'
        })
        self.patcher_env.start()
        
        # Create test data
        self.reddit_context = RedditContext(
            post_id='test_post_id',
            post_title='Test Post Title',
            post_url='https://reddit.com/test',
            subreddit='test_subreddit'
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
                image_local_path="/path/to/image1.jpg"
            )
        ]
        
        yield
        
        self.patcher_env.stop()

    @patch('app.main.save_to_csv')
    @patch('app.main.RedditAgent')
    async def test_end_to_end_flow_success_simplified(self, mock_reddit_agent, mock_save_to_csv):
        # Configure mock_reddit_agent to return a successful product info
        mock_reddit_agent_instance = MagicMock()
        mock_reddit_agent.return_value = mock_reddit_agent_instance
        mock_reddit_agent_instance.find_and_create_product = AsyncMock(return_value=self.mock_products_data[0])

        # Run the full pipeline function directly instead of main()
        await run_full_pipeline()

        # Verify RedditAgent was initialized and its methods were called
        mock_reddit_agent.assert_called_once()
        mock_reddit_agent_instance.find_and_create_product.assert_called_once()

        # Verify save_to_csv was called with the correct data
        mock_save_to_csv.assert_called_once_with(self.mock_products_data[0])

    @patch('app.main.save_to_csv')
    @patch('app.main.RedditAgent')
    async def test_test_voting_mode(self, mock_reddit_agent, mock_save_to_csv):
        # Configure mock_reddit_agent
        mock_reddit_agent_instance = MagicMock()
        mock_reddit_agent.return_value = mock_reddit_agent_instance
        
        # Mock a trending post
        mock_post = MagicMock()
        mock_post.title = "Test Post"
        mock_post.permalink = "/r/golf/comments/test123"
        mock_post.id = "test123"
        # Return an iterator for subreddit.hot()
        mock_reddit_agent_instance.reddit.subreddit.return_value.hot.return_value = iter([mock_post])
        
        # Mock the voting behavior
        mock_reddit_agent_instance.interact_with_votes = AsyncMock(return_value="upvote")
        
        # Run the test voting function
        from app.main import test_reddit_voting
        await test_reddit_voting()
        
        # Verify the Reddit agent was used correctly
        mock_reddit_agent.assert_called_once()
        mock_reddit_agent_instance.reddit.subreddit.assert_called_once_with("golf")
        mock_reddit_agent_instance.interact_with_votes.assert_called_once_with("test123")

    @patch('app.affiliate_linker.ZazzleAffiliateLinker')
    @patch('app.content_generator.ContentGenerator')
    @patch('app.agents.reddit_agent.RedditAgent')
    async def test_full_pipeline(self, mock_reddit_agent, mock_content_generator, mock_affiliate_linker):
        # Setup mocks
        mock_reddit_agent.return_value.get_reddit_posts.return_value = [
            ProductIdea(
                theme="Test Post",
                image_description="Test image description",
                design_instructions={"image": "https://example.com/test.jpg"},
                reddit_context=self.reddit_context,
                model="dall-e-3",
                prompt_version="1.0.0"
            )
        ]

        mock_content_generator.return_value.generate_content.return_value = self.mock_products_data

        mock_affiliate_linker_instance = mock_affiliate_linker.return_value
        mock_affiliate_linker_instance.generate_links_batch.return_value = self.mock_products_data

        # Run pipeline
        config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id="test_template_id",
            zazzle_tracking_code="test_tracking_code",
            prompt_version="1.0.0"
        )

        await run_full_pipeline(config)

    @patch('app.affiliate_linker.ZazzleAffiliateLinker')
    @patch('app.content_generator.ContentGenerator')
    @patch('app.agents.reddit_agent.RedditAgent')
    async def test_pipeline_error_handling(self, mock_reddit_agent, mock_content_generator, mock_affiliate_linker):
        # Setup mocks to raise exceptions
        mock_agent = AsyncMock(spec=RedditAgent)
        mock_agent.find_and_create_product.side_effect = Exception("Reddit API error")
        mock_agent.reddit = MagicMock()
        mock_reddit_agent.return_value = mock_agent

        # Run pipeline
        config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id="test_template_id",
            zazzle_tracking_code="test_tracking_code",
            prompt_version="1.0.0"
        )

        with pytest.raises(Exception) as exc_info:
            await run_full_pipeline(config)
            assert "Reddit API error" in str(exc_info.value)

    @patch('app.affiliate_linker.ZazzleAffiliateLinker')
    @patch('app.content_generator.ContentGenerator')
    @patch('app.agents.reddit_agent.RedditAgent')
    async def test_pipeline_no_products(self, mock_reddit_agent, mock_content_generator, mock_affiliate_linker):
        # Setup mocks to return empty lists
        mock_reddit_agent.return_value.get_reddit_posts.return_value = []
        mock_content_generator.return_value.generate_content.return_value = []

        # Run pipeline
        config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id="test_template_id",
            zazzle_tracking_code="test_tracking_code",
            prompt_version="1.0.0"
        )

        result = await run_full_pipeline(config)
        assert result is None

    @patch('builtins.open', new_callable=mock_open)
    @patch('csv.DictWriter')
    async def test_save_to_csv(self, mock_dict_writer, mock_file):
        # Test saving products to CSV
        # Set up the mock to return a mock writer
        mock_writer = MagicMock()
        mock_dict_writer.return_value = mock_writer
        
        # Mock os.path.exists to return False to test header writing
        with patch('app.main.os.path.exists', return_value=False):
            save_to_csv(self.mock_products_data)

        # Check that open was called with a file ending in 'processed_products.csv'
        open_call_args = mock_file.call_args[0][0]
        assert open_call_args.endswith('processed_products.csv')
        mock_dict_writer.assert_called_once()
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerows.assert_called_once()

if __name__ == '__main__':
    unittest.main() 