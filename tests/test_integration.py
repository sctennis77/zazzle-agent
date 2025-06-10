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
from app.models import Product, ContentType
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

        # Mock product data as a list of dictionaries, matching config file structure
        self.mock_products_data = [
            {"product_id": "ID_A", "name": "Product A", "screenshot_path": "outputs/screenshots/ID_A.png"},
            {"product_id": "ID_B", "name": "Product B", "screenshot_path": "outputs/screenshots/ID_B.png"},
            {"product_id": "ID_C", "name": "Product C", "screenshot_path": "outputs/screenshots/ID_C.png"},
        ]
        # A mock Product object for process_product tests
        self.mock_product_object = Product(product_id="ID_A", name="Product A", screenshot_path="outputs/screenshots/ID_A.png")

        # Create dummy config file for tests that read it
        self.dummy_config_dir = 'app'
        self.dummy_config_path = os.path.join(self.dummy_config_dir, 'products_config.json')
        with open(self.dummy_config_path, 'w') as f:
            json.dump({'products': self.mock_products_data}, f, indent=4)
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
        test_product = {
            "product_url": "http://test.com/product",
            "text": "Test text",
            "image_url": "http://test.com/image.png",
            "reddit_post_id": "id1",
            "reddit_post_title": "title1",
            "reddit_post_url": "url1",
            "created_at": "2023-01-01T12:00:00+00:00",
            "design_instructions": "Create a cheerful cartoon golf ball with sunglasses."
        }
        save_to_csv(test_product)
        mock_makedirs.assert_not_called()  # No makedirs in new version
        mock_open.assert_called_once_with('processed_products.csv', 'a', newline='')
        mock_dict_writer.assert_called_once()
        mock_dict_writer.return_value.writeheader.assert_called_once()
        mock_dict_writer.return_value.writerow.assert_called_once()
        # Verify design_instructions is included
        assert 'design_instructions' in mock_dict_writer.call_args[1]['fieldnames']

    @patch('app.main.os.makedirs')
    @patch('builtins.open', side_effect=Exception("Open error")) # Patch open to raise an exception
    def test_save_to_csv_error(self, mock_open, mock_makedirs):
        test_product = {
            "product_url": "http://test.com/product",
            "text": "Test text",
            "image_url": "http://test.com/image.png",
            "reddit_post_id": "id1",
            "reddit_post_title": "title1",
            "reddit_post_url": "url1",
            "created_at": "2023-01-01T12:00:00+00:00"
        }
        with self.assertRaises(Exception) as cm:
            save_to_csv(test_product)
        self.assertIn("Open error", str(cm.exception))
        mock_makedirs.assert_not_called()  # No makedirs in new version

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
        
        yield
        
        self.patcher_env.stop()

    @patch('app.main.save_to_csv')
    @patch('app.main.RedditAgent')
    async def test_end_to_end_flow_success_simplified(self, mock_reddit_agent, mock_save_to_csv):
        # Configure mock_reddit_agent to return a successful product info
        mock_reddit_agent_instance = MagicMock()
        mock_reddit_agent.return_value = mock_reddit_agent_instance
        mock_reddit_agent_instance.find_and_create_product = AsyncMock(return_value={
            'product_url': 'http://test.zazzle.com/generated_product',
            'text': 'Generated Text',
            'image_url': 'http://test.image.com/generated_image.png',
            'theme': 'test_theme',
            'reddit_context': {'id': 'post_id', 'title': 'Post Title', 'url': 'http://reddit.com/post', 'created_utc': 1234567890}
        })

        # Run the full pipeline function directly instead of main()
        await run_full_pipeline()

        # Verify RedditAgent was initialized and its methods were called
        mock_reddit_agent.assert_called_once()
        mock_reddit_agent_instance.find_and_create_product.assert_called_once()

        # Verify save_to_csv was called with the correct data
        mock_save_to_csv.assert_called_once()
        called_product = mock_save_to_csv.call_args[0][0]
        assert called_product['product_url'] == 'http://test.zazzle.com/generated_product'
        assert called_product['text'] == 'Generated Text'
        assert called_product['theme'] == 'test_theme'
        reddit_context = called_product['reddit_context']
        assert reddit_context['id'] == 'post_id'
        assert reddit_context['title'] == 'Post Title'

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

if __name__ == '__main__':
    unittest.main() 