import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
import math
from app.main import main, process_product, save_to_csv, load_products
from app.affiliate_linker import ZazzleAffiliateLinker, ZazzleAffiliateLinkerError, InvalidProductDataError
from app.content_generator import ContentGenerator
import logging # Import logging to check log output
from datetime import datetime
from app.models import Product
import pytest
import json
import glob
import shutil # Import shutil for cleanup

class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Mock necessary environment variables for tests
        self.patcher_env = patch.dict(os.environ, {
            'ZAZZLE_AFFILIATE_ID': 'test_affiliate_id',
            'OPENAI_API_KEY': 'test_openai_key',
            'SCRAPE_DELAY': '0', # Mock delay for scraper (though scraper is removed)
            'MAX_PRODUCTS': '3' # Max products to process from config
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
        os.makedirs(self.dummy_config_dir, exist_ok=True)
        with open(self.dummy_config_path, 'w') as f:
             json.dump(self.mock_products_data, f)

        # Create dummy screenshot directory and file for tests
        self.dummy_outputs_dir = 'outputs'
        self.dummy_screenshot_dir = os.path.join(self.dummy_outputs_dir, 'screenshots')
        self.dummy_screenshot_path = os.path.join(self.dummy_screenshot_dir, 'ID_A.png')
        os.makedirs(self.dummy_screenshot_dir, exist_ok=True)
        # Create a dummy file to simulate a screenshot existing
        with open(self.dummy_screenshot_path, 'w') as f:
            f.write('dummy image data')

    def tearDown(self):
        # Clean up dummy config file and outputs directory
        if os.path.exists(self.dummy_config_path):
            os.remove(self.dummy_config_path)
        # Be careful with recursive deletion, ensure it's only the test output directory
        if os.path.exists(self.dummy_outputs_dir):
             shutil.rmtree(self.dummy_outputs_dir)

    def test_process_product_success(self):
        # Mock components
        mock_linker = MagicMock(spec=ZazzleAffiliateLinker)
        mock_linker.generate_affiliate_link.return_value = "http://testlink.com/ID_A?rf=test_affiliate_id"
        
        mock_content_gen = MagicMock(spec=ContentGenerator)
        mock_content_gen.generate_tweet_content.return_value = "Test tweet content"
        
        # Test successful product processing
        result = process_product(self.mock_product_object, mock_linker, mock_content_gen)
        
        self.assertEqual(result.product_id, "ID_A")
        self.assertEqual(result.name, "Product A")
        self.assertEqual(result.affiliate_link, "http://testlink.com/ID_A?rf=test_affiliate_id")
        self.assertEqual(result.tweet_text, "Test tweet content")
        self.assertEqual(result.screenshot_path, "outputs/screenshots/ID_A.png")
        self.assertIsNotNone(result.identifier)

    def test_process_product_affiliate_link_error(self):
        # Mock components
        mock_linker = MagicMock(spec=ZazzleAffiliateLinker)
        mock_linker.generate_affiliate_link.side_effect = ZazzleAffiliateLinkerError("Test error")
        
        mock_content_gen = MagicMock(spec=ContentGenerator)
        mock_content_gen.generate_tweet_content.return_value = "Test tweet content"
        
        # Test product processing with affiliate link error
        with self.assertRaises(ZazzleAffiliateLinkerError):
            process_product(self.mock_product_object, mock_linker, mock_content_gen)

    @patch('app.main.ZazzleAffiliateLinker')
    @patch('app.main.ContentGenerator')
    def test_process_product_content_error(self, mock_content_gen, mock_linker):
        # Mock content generator to raise an error
        mock_content_gen_instance = MagicMock(spec=ContentGenerator)
        mock_content_gen_instance.generate_tweet_content.side_effect = Exception("Test error")
        mock_content_gen.return_value = mock_content_gen_instance

        # Mock linker
        mock_linker_instance = MagicMock(spec=ZazzleAffiliateLinker)
        mock_linker_instance.generate_affiliate_link.return_value = "http://testlink.com/ID_A?rf=test_affiliate_id"
        mock_linker.return_value = mock_linker_instance

        # Test product processing with content generation error
        # process_product catches the exception and sets tweet_text to an error message
        result = process_product(self.mock_product_object, mock_linker_instance, mock_content_gen_instance)

        self.assertIsNotNone(result.affiliate_link)
        self.assertEqual(result.tweet_text, "Error generating tweet content") # Expect the error message without trailing dot

        # Verify generator was called
        mock_content_gen_instance.generate_tweet_content.assert_called_once_with("Product A")

    @patch('app.main.os.makedirs')
    @patch('app.main.pd.DataFrame')
    def test_save_to_csv_success(self, mock_dataframe_class, mock_makedirs):
        # Test data - use Product objects including screenshot_path
        test_products = [
            Product(product_id="ID_A", name="Product A", affiliate_link="http://testlink.com/ID_A", tweet_text="Test tweet A", screenshot_path="outputs/screenshots/ID_A.png"),
            Product(product_id="ID_B", name="Product B", affiliate_link="http://testlink.com/ID_B", tweet_text="Test tweet B", screenshot_path="outputs/screenshots/ID_B.png")
        ]

        # Mock pandas DataFrame
        mock_df = MagicMock()
        mock_df.to_csv = MagicMock()

        with patch('pandas.DataFrame', return_value=mock_df) as mock_df_constructor:
            # Test saving to new file (force is removed)
            save_to_csv(test_products)

            # Verify DataFrame was created with correct data (check column names and number of rows)
            # The actual data check might be more involved, this is a basic check
            mock_df_constructor.assert_called_once()
            # Check the data passed to DataFrame constructor
            called_data = mock_df_constructor.call_args[0][0]
            self.assertEqual(len(called_data), 2)
            self.assertIn('product_id', called_data[0])
            self.assertIn('name', called_data[0])
            self.assertIn('affiliate_link', called_data[0])
            self.assertIn('tweet_text', called_data[0])
            self.assertIn('identifier', called_data[0]) # Identifier is still expected in CSV output
            self.assertIn('screenshot_path', called_data[0]) # Check for screenshot_path column

            # Verify to_csv was called once with correct arguments
            mock_df.to_csv.assert_called_once()
            call_args, call_kwargs = mock_df.to_csv.call_args
            self.assertTrue(call_args[0].endswith('.csv')) # Check filename pattern
            self.assertFalse(call_kwargs.get('index', False)) # Check index=False

        # Verify outputs directory was created
        mock_makedirs.assert_called_once_with('outputs', exist_ok=True)

    def test_save_to_csv_error(self):
        # Test data
        test_products = [
            Product(product_id="ID_A", name="Product A", affiliate_link="http://testlink.com/ID_A", tweet_text="Test tweet A", screenshot_path="outputs/screenshots/ID_A.png")
        ]
        
        # Mock pandas DataFrame to raise an error
        with patch('pandas.DataFrame', side_effect=Exception("Test error")):
            with self.assertRaises(Exception):
                save_to_csv(test_products)

    @patch('app.main.ContentGenerator')
    @patch('app.main.ZazzleAffiliateLinker')
    @patch('app.main.json.load', autospec=True)
    @patch('builtins.open', new_callable=mock_open)
    @patch('app.main.os.path.exists', return_value=True)
    @patch('app.main.os.makedirs')
    @patch('app.main.pd.DataFrame')
    @patch('app.main.pd.read_csv')
    @patch('glob.glob')
    @patch('os.path.getctime', return_value=0)
    def test_end_to_end_flow_success(self, mock_getctime, mock_glob, mock_read_csv, mock_dataframe_class, mock_makedirs, mock_path_exists, mock_open, mock_json_load, mock_linker, mock_content_gen):
        # Configure mocks
        mock_json_load.return_value = self.mock_products_data
        
        mock_linker_instance = MagicMock()
        mock_linker.return_value = mock_linker_instance
        mock_linker_instance.generate_affiliate_link.side_effect = lambda product_id, name: f"http://testlink.com/{product_id}?rf=test_affiliate_id"
        
        mock_content_gen_instance = MagicMock()
        mock_content_gen.return_value = mock_content_gen_instance
        mock_content_gen_instance.generate_tweet_content.side_effect = lambda product_name, force_new_content: f"Tweet for {product_name}."
        
        mock_df_instance = MagicMock()
        mock_dataframe_class.return_value = mock_df_instance
        
        # Mock empty existing CSV
        mock_glob.return_value = ['outputs/listings_20250605_123456.csv']
        mock_read_csv.return_value = pd.DataFrame()
        
        # Run main function
        main()
        
        # Verify component initialization
        mock_linker.assert_called_once_with(affiliate_id='test_affiliate_id')
        mock_content_gen.assert_called_once_with(api_key='test_openai_key')
        
        # Verify product processing
        self.assertEqual(mock_linker_instance.generate_affiliate_link.call_count, len(self.mock_products_data))
        self.assertEqual(mock_content_gen_instance.generate_tweet_content.call_count, len(self.mock_products_data))
        
        # Verify CSV operations
        makedirs_calls = [call for call in mock_makedirs.call_args_list if call == (('outputs',), {'exist_ok': True})]
        self.assertTrue(len(makedirs_calls) >= 1)
        mock_df_instance.to_csv.assert_called_once()

    @pytest.mark.xfail(reason="Testing error handling for missing config file")
    @patch('app.main.json.load', autospec=True)
    @patch('builtins.open', side_effect=FileNotFoundError("Config file not found"))
    @patch('app.main.os.path.exists', return_value=False)
    def test_end_to_end_flow_config_error(self, mock_path_exists, mock_open, mock_json_load):
        with patch('builtins.print') as mock_print:
            main()
            mock_open.assert_called_with('app/products_config.json', 'r')
            mock_json_load.assert_not_called()

    @patch('app.main.ContentGenerator')
    @patch('app.main.ZazzleAffiliateLinker')
    @patch('app.main.json.load', autospec=True)
    @patch('builtins.open', new_callable=mock_open)
    def test_end_to_end_flow_missing_env_vars(self, mock_open, mock_json_load, mock_linker, mock_content_gen):
        # Test with missing ZAZZLE_AFFILIATE_ID
        with patch.dict(os.environ, {'ZAZZLE_AFFILIATE_ID': ''}, clear=True):
            main()
            mock_linker.assert_not_called()
            mock_content_gen.assert_not_called()
        
        # Test with missing OPENAI_API_KEY
        with patch.dict(os.environ, {
            'ZAZZLE_AFFILIATE_ID': 'test_id',
            'OPENAI_API_KEY': ''
        }, clear=True):
            main()
            mock_content_gen.assert_not_called()

    @patch('app.main.os.makedirs')
    @patch('app.main.pd.DataFrame')
    def test_save_to_csv_error(self, mock_dataframe_class, mock_makedirs):
        # Test data - use Product objects including screenshot_path
        test_products = [
            Product(product_id="ID_A", name="Product A", screenshot_path="outputs/screenshots/ID_A.png")
        ]

        # Mock pandas DataFrame to raise an error on to_csv
        mock_df = MagicMock()
        mock_df.to_csv.side_effect = Exception("CSV save error")
        mock_dataframe_class.return_value = mock_df

        # Test saving to CSV with error
        with self.assertRaises(Exception) as cm:
            save_to_csv(test_products)
        self.assertIn("CSV save error", str(cm.exception))

        # Verify outputs directory was created
        mock_makedirs.assert_called_once_with('outputs', exist_ok=True)

    @patch('builtins.open', new_callable=MagicMock)
    @patch('app.main.json.load')
    def test_load_products_includes_screenshot_path(self, mock_json_load, mock_open):
        # Configure mock json.load to return data with screenshot_path
        mock_config_data = [
             {"product_id": "ID_A", "name": "Product A", "screenshot_path": "outputs/screenshots/ID_A.png"},
             {"product_id": "ID_B", "name": "Product B", "screenshot_path": "outputs/screenshots/ID_B.png"},
        ]
        mock_json_load.return_value = mock_config_data

        products = load_products()

        # Assert that products are loaded correctly and screenshot_path is included
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0].product_id, "ID_A")
        self.assertEqual(products[0].name, "Product A")
        self.assertEqual(products[0].screenshot_path, "outputs/screenshots/ID_A.png")
        self.assertEqual(products[1].product_id, "ID_B")
        self.assertEqual(products[1].name, "Product B")
        self.assertEqual(products[1].screenshot_path, "outputs/screenshots/ID_B.png")

        # Test a product without screenshot_path in config
        mock_config_data_no_screenshot = [
             {"product_id": "ID_C", "name": "Product C"},
        ]
        mock_json_load.return_value = mock_config_data_no_screenshot

        products_no_screenshot = load_products()

        self.assertEqual(len(products_no_screenshot), 1)
        self.assertEqual(products_no_screenshot[0].product_id, "ID_C")
        self.assertEqual(products_no_screenshot[0].name, "Product C")
        self.assertIsNone(products_no_screenshot[0].screenshot_path) # Should be None

if __name__ == '__main__':
    unittest.main() 