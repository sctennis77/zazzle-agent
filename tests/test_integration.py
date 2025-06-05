import os
import unittest
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
import math
from app.main import main
from app.affiliate_linker import ZazzleAffiliateLinker
from app.content_generator import ContentGenerator
import logging # Import logging to check log output

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
        os.makedirs(self.outputs_dir, exist_ok=True)
        # Patch the outputs directory creation/usage if necessary in main.py or other places
        # However, since main.py no longer saves to CSV, this might not be strictly needed for current tests.

    def tearDown(self):
        # Clean up the temporary outputs directory
        if os.path.exists(self.outputs_dir):
            import shutil
            shutil.rmtree(self.outputs_dir)

    @patch('app.main.ContentGenerator') # Patch ContentGenerator in app.main
    @patch('app.main.ZazzleAffiliateLinker') # Patch ZazzleAffiliateLinker in app.main
    @patch('app.main.json.load', autospec=True) # Patch json.load in app.main
    @patch('builtins.open', new_callable=mock_open) # Patch open in app.main
    @patch('app.main.os.path.exists', return_value=True) # Mock path.exists for config file
    def test_end_to_end_flow_success(self, mock_path_exists, mock_open, mock_json_load, mock_linker, mock_content_gen):
        # Configure mock json.load to return our mock product data
        mock_json_load.return_value = self.mock_products_data

        # Configure mock linker instance
        mock_linker_instance = MagicMock()
        mock_linker.return_value = mock_linker_instance
        mock_linker_instance.generate_affiliate_link.side_effect = lambda product: f"http://testlink.com/{product['product_id']}?rf=test_affiliate_id"
        mock_linker_instance.generate_links_batch.side_effect = lambda products: [{'product_id': p['product_id'], 'affiliate_link': f"http://testlink.com/{p['product_id']}?rf=test_affiliate_id"} for p in products]

        # Configure mock content generator instance
        mock_content_gen_instance = MagicMock()
        mock_content_gen.return_value = mock_content_gen_instance
        mock_content_gen_instance.generate_tweet_content.side_effect = lambda product: f"Tweet for {product['name']}."
        # Note: The main function now processes products one by one, so generate_tweets_batch might not be called.
        # Adjusting mock to match the main function's loop.
        mock_content_gen_instance.generate_tweets_batch.side_effect = lambda products: products # Fallback if needed

        # Patch print to capture output
        with patch('builtins.print') as mock_print:
            # Run the main function
            main()

            # Assert that json.load and open were called for the config file
            mock_open.assert_called_with('app/products_config.json', 'r')
            mock_json_load.assert_called_once()

            # Assert that linker and content generator were initialized with correct arguments
            mock_linker.assert_called_once_with(affiliate_id='test_affiliate_id')
            mock_content_gen.assert_called_once_with(api_key='test_openai_key')

            # Assert that generate_affiliate_link and generate_tweet_content were called for each product
            self.assertEqual(mock_linker_instance.generate_affiliate_link.call_count, len(self.mock_products_data))
            self.assertEqual(mock_content_gen_instance.generate_tweet_content.call_count, len(self.mock_products_data))

            # Assert that print was called for each product with the generated information
            expected_prints = []
            for product in self.mock_products_data:
                 expected_prints.append(f"Product ID: {product['product_id']}")
                 expected_prints.append(f"Name: {product['name']}")
                 expected_prints.append(f"Affiliate Link: http://testlink.com/{product['product_id']}?rf=test_affiliate_id")
                 expected_prints.append(f"Tweet Content: Tweet for {product['name']}.")
                 expected_prints.append("---")

            mock_print.assert_has_calls([unittest.mock.call(p) for p in expected_prints], any_order=False)

    @patch('app.main.ContentGenerator')
    @patch('app.main.ZazzleAffiliateLinker')
    @patch('app.main.json.load', autospec=True) # Patch json.load in app.main
    @patch('builtins.open', new_callable=mock_open) # Patch open in app.main
    @patch('app.main.os.path.exists', return_value=True) # Mock path.exists for config file
    @patch('app.main.logger.warning') # Patch logger.warning to check for specific log messages
    def test_end_to_end_flow_no_products(self, mock_warning_logger, mock_path_exists, mock_open, mock_json_load, mock_linker, mock_content_gen):
        # Configure mock json.load to return an empty list
        mock_json_load.return_value = []

        # Run the main function
        main()

        # Assert that json.load and open were called for the config file
        mock_open.assert_called_with('app/products_config.json', 'r')
        mock_json_load.assert_called_once()

        # Assert that linker and content generator were NOT initialized
        mock_linker.assert_not_called()
        mock_content_gen.assert_not_called()

        # Assert that the expected warning message was logged
        mock_warning_logger.assert_called_once_with("No products found in the configuration file.")

    @patch('app.main.ContentGenerator')
    @patch('app.main.ZazzleAffiliateLinker')
    @patch('app.main.json.load', autospec=True) # Patch json.load in app.main
    @patch('builtins.open', new_callable=mock_open) # Patch open in app.main
    @patch('app.main.os.path.exists', return_value=True) # Mock path.exists for config file
    def test_end_to_end_flow_openai_error(self, mock_path_exists, mock_open, mock_json_load, mock_linker, mock_content_gen):
        # Configure mock json.load to return our mock product data
        mock_json_load.return_value = self.mock_products_data

        # Configure mock linker instance (successful linking)
        mock_linker_instance = MagicMock()
        mock_linker.return_value = mock_linker_instance
        mock_linker_instance.generate_affiliate_link.side_effect = lambda product: f"http://testlink.com/{product['product_id']}?rf=test_affiliate_id"

        # Configure mock content generator instance to raise an exception
        mock_content_gen_instance = MagicMock()
        mock_content_gen.return_value = mock_content_gen_instance
        mock_content_gen_instance.generate_tweet_content.side_effect = Exception("Simulated OpenAI API error")

        # Patch print to capture output
        with patch('builtins.print') as mock_print:
            # Run the main function
            main()

            # Assert that json.load and open were called for the config file
            mock_open.assert_called_with('app/products_config.json', 'r')
            mock_json_load.assert_called_once()

            # Assert that linker and content generator were initialized
            mock_linker.assert_called_once_with(affiliate_id='test_affiliate_id')
            mock_content_gen.assert_called_once_with(api_key='test_openai_key')

            # Assert that generate_affiliate_link was called for each product
            self.assertEqual(mock_linker_instance.generate_affiliate_link.call_count, len(self.mock_products_data))

            # Assert that generate_tweet_content was called for each product
            self.assertEqual(mock_content_gen_instance.generate_tweet_content.call_count, len(self.mock_products_data))

            # Assert that print was called for each product, including the error message for the tweet
            expected_prints = []
            for product in self.mock_products_data:
                 expected_prints.append(f"Product ID: {product['product_id']}")
                 expected_prints.append(f"Name: {product['name']}")
                 expected_prints.append(f"Affiliate Link: http://testlink.com/{product['product_id']}?rf=test_affiliate_id")
                 # Expecting the error message for the tweet due to error handling in main
                 expected_prints.append(f"Tweet Content: Error generating tweet content.")
                 expected_prints.append("---")

            mock_print.assert_has_calls([unittest.mock.call(p) for p in expected_prints], any_order=False)

    # Test case for error reading config file (e.g., FileNotFoundError)
    @patch('app.main.json.load', autospec=True) # Patch json.load in app.main
    @patch('builtins.open', side_effect=FileNotFoundError("Config file not found")) # Patch open to raise error
    @patch('app.main.os.path.exists', return_value=False) # Mock path.exists for config file
    def test_end_to_end_flow_config_error(self, mock_path_exists, mock_open, mock_json_load):
         with patch('builtins.print') as mock_print:
             main()

             # Assert that open was called and raised FileNotFoundError
             mock_open.assert_called_with('app/products_config.json', 'r')

             # Assert that json.load, linker, and content generator were NOT called
             mock_json_load.assert_not_called()

    # The test_end_to_end_flow_scraper_error test is no longer relevant as scraping is removed.
    # I will remove it.

if __name__ == '__main__':
    unittest.main() 