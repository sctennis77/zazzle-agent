import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
import math
from app.main import main, process_product, save_to_csv
from app.affiliate_linker import ZazzleAffiliateLinker, ZazzleAffiliateLinkerError, InvalidProductDataError
from app.content_generator import ContentGenerator
import logging # Import logging to check log output
from datetime import datetime

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

        # Mock product data that would typically come from scraping (now from config)
        self.mock_products_data = [
            {'product_id': 'ID_A', 'name': 'Product A'},
            {'product_id': 'ID_B', 'name': 'Product B'},
            {'product_id': 'ID_C', 'name': 'Product C'},
        ]

        # Mock OpenAI response
        self.mock_openai_response = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated tweet for Product."))]
        )

        # Create a temporary outputs directory for testing file saving (if still applicable)
        # Note: Main function no longer saves to CSV, but keeping this in case of future changes
        self.outputs_dir = 'test_outputs'
        # No need to os.makedirs here, will mock it in the test

    def tearDown(self):
        # Clean up the temporary outputs directory (if it were actually created by the test)
        # Since we are mocking, actual directory creation is prevented. Clean up is less critical.
        # However, if the mock was imperfect or for future changes, keeping cleanup is good practice.
        # In this mocked scenario, we don't need to remove a directory.
        pass # Removed shutil.rmtree(self.outputs_dir)

    def test_process_product_success(self):
        # Mock components
        mock_linker = MagicMock(spec=ZazzleAffiliateLinker)
        mock_linker.generate_affiliate_link.return_value = "http://testlink.com/ID_A?rf=test_affiliate_id"
        
        mock_content_gen = MagicMock(spec=ContentGenerator)
        mock_content_gen.generate_tweet_content.return_value = "Test tweet content"
        
        # Test successful product processing
        result = process_product(
            self.mock_products_data[0],
            mock_linker,
            mock_content_gen,
            force_new_content=True
        )
        
        self.assertEqual(result['product_id'], 'ID_A')
        self.assertEqual(result['name'], 'Product A')
        self.assertEqual(result['affiliate_link'], "http://testlink.com/ID_A?rf=test_affiliate_id")
        self.assertEqual(result['tweet_text'], "Test tweet content")
        self.assertTrue('identifier' in result)

    def test_process_product_affiliate_link_error(self):
        # Mock components
        mock_linker = MagicMock(spec=ZazzleAffiliateLinker)
        mock_linker.generate_affiliate_link.side_effect = ZazzleAffiliateLinkerError("Test error")
        
        mock_content_gen = MagicMock(spec=ContentGenerator)
        mock_content_gen.generate_tweet_content.return_value = "Test tweet content"
        
        # Test product processing with affiliate link error
        result = process_product(
            self.mock_products_data[0],
            mock_linker,
            mock_content_gen,
            force_new_content=True
        )
        
        self.assertEqual(result['product_id'], 'ID_A')
        self.assertEqual(result['name'], 'Product A')
        self.assertEqual(result['affiliate_link'], "Error generating affiliate link")
        self.assertEqual(result['tweet_text'], "Test tweet content")
        self.assertTrue('identifier' in result)

    def test_process_product_content_error(self):
        # Mock components
        mock_linker = MagicMock(spec=ZazzleAffiliateLinker)
        mock_linker.generate_affiliate_link.return_value = "http://testlink.com/ID_A?rf=test_affiliate_id"
        
        mock_content_gen = MagicMock(spec=ContentGenerator)
        mock_content_gen.generate_tweet_content.side_effect = Exception("Test error")
        
        # Test product processing with content generation error
        result = process_product(
            self.mock_products_data[0],
            mock_linker,
            mock_content_gen,
            force_new_content=True
        )
        
        self.assertEqual(result['product_id'], 'ID_A')
        self.assertEqual(result['name'], 'Product A')
        self.assertEqual(result['affiliate_link'], "http://testlink.com/ID_A?rf=test_affiliate_id")
        self.assertEqual(result['tweet_text'], "Error generating tweet content.")
        self.assertTrue('identifier' in result)

    def test_save_to_csv_success(self):
        # Test data
        test_products = [
            {
                'product_id': 'ID_A',
                'name': 'Product A',
                'affiliate_link': 'http://testlink.com/ID_A',
                'tweet_text': 'Test tweet A'
            },
            {
                'product_id': 'ID_B',
                'name': 'Product B',
                'affiliate_link': 'http://testlink.com/ID_B',
                'tweet_text': 'Test tweet B'
            }
        ]
        
        # Mock pandas DataFrame
        mock_df = MagicMock()
        mock_df.to_csv = MagicMock()
        
        with patch('pandas.DataFrame', return_value=mock_df):
            # Test saving to new file
            save_to_csv(test_products, force=True)
            mock_df.to_csv.assert_called_once()
            
            # Test saving to existing file
            with patch('glob.glob', return_value=['outputs/listings_20250101_000000.csv']):
                with patch('os.path.getctime', return_value=0):
                    save_to_csv(test_products, force=False)
                    self.assertEqual(mock_df.to_csv.call_count, 2)

    def test_save_to_csv_error(self):
        # Test data
        test_products = [
            {
                'product_id': 'ID_A',
                'name': 'Product A',
                'affiliate_link': 'http://testlink.com/ID_A',
                'tweet_text': 'Test tweet A'
            }
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
        mock_linker_instance.generate_affiliate_link.side_effect = lambda product: f"http://testlink.com/{product['product_id']}?rf=test_affiliate_id"
        
        mock_content_gen_instance = MagicMock()
        mock_content_gen.return_value = mock_content_gen_instance
        mock_content_gen_instance.generate_tweet_content.side_effect = lambda product: f"Tweet for {product['name']}."
        
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
        mock_makedirs.assert_called_once_with('outputs', exist_ok=True)
        mock_df_instance.to_csv.assert_called_once()

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

if __name__ == '__main__':
    unittest.main() 