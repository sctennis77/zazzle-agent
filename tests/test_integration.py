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
        # No need to os.makedirs here, will mock it in the test

    def tearDown(self):
        # Clean up the temporary outputs directory (if it were actually created by the test)
        # Since we are mocking, actual directory creation is prevented. Clean up is less critical.
        # However, if the mock was imperfect or for future changes, keeping cleanup is good practice.
        # In this mocked scenario, we don't need to remove a directory.
        pass # Removed shutil.rmtree(self.outputs_dir)

    @patch('app.main.ContentGenerator')
    @patch('app.main.ZazzleAffiliateLinker')
    @patch('app.main.json.load', autospec=True)
    @patch('builtins.open', new_callable=mock_open)
    @patch('app.main.os.path.exists', return_value=True)
    @patch('app.main.os.makedirs')
    @patch('app.main.pd.DataFrame')
    def test_end_to_end_flow_success(self, mock_dataframe_class, mock_makedirs, mock_path_exists, mock_open, mock_json_load, mock_linker, mock_content_gen):
        # Configure mock json.load to return our mock product data
        mock_json_load.return_value = self.mock_products_data

        # Configure mock linker instance
        mock_linker_instance = MagicMock()
        mock_linker.return_value = mock_linker_instance
        mock_linker_instance.generate_affiliate_link.side_effect = lambda product: f"http://testlink.com/{product['product_id']}?rf=test_affiliate_id"

        # Configure mock content generator instance
        mock_content_gen_instance = MagicMock()
        mock_content_gen.return_value = mock_content_gen_instance
        mock_content_gen_instance.generate_tweet_content.side_effect = lambda product: f"Tweet for {product['name']}."

        # Mock DataFrame instance and its to_csv method
        mock_df_instance = MagicMock()
        mock_df_instance.__getitem__.return_value = mock_df_instance
        mock_dataframe_class.return_value = mock_df_instance

        # Run the main function
        main()

        # Assert that json.load and open were called for the config file
        mock_open.assert_any_call('app/products_config.json', 'r')
        mock_json_load.assert_called_once()

        # Assert that linker and content generator were initialized with correct arguments
        mock_linker.assert_called_once_with(affiliate_id='test_affiliate_id')
        mock_content_gen.assert_called_once_with(api_key='test_openai_key')

        # Assert that generate_affiliate_link and generate_tweet_content were called for each product
        self.assertEqual(mock_linker_instance.generate_affiliate_link.call_count, len(self.mock_products_data))
        self.assertEqual(mock_content_gen_instance.generate_tweet_content.call_count, len(self.mock_products_data))

        # Assert that the outputs directory was ensured
        mock_makedirs.assert_called_once_with('outputs', exist_ok=True)

        # Assert that a DataFrame was created with the processed product data
        expected_processed_data = []
        for product in self.mock_products_data:
            expected_processed_data.append({
                'product_id': product['product_id'],
                'name': product['name'],
                'title': product['name'],
                'affiliate_link': f"http://testlink.com/{product['product_id']}?rf=test_affiliate_id",
                'tweet_text': f"Tweet for {product['name']}."
            })

        # Verify DataFrame was created with correct data
        mock_dataframe_class.assert_called_once()
        actual_processed_data = mock_dataframe_class.call_args[0][0]
        self.assertEqual(actual_processed_data, expected_processed_data)

        # Verify to_csv was called
        mock_df_instance.to_csv.assert_called_once()
        call_args, call_kwargs = mock_df_instance.to_csv.call_args
        self.assertRegex(call_args[0], r'outputs/listings_\d{8}_\d{6}.csv')
        self.assertEqual(call_kwargs.get('index'), False)

    @patch('app.main.ContentGenerator')
    @patch('app.main.ZazzleAffiliateLinker')
    @patch('app.main.json.load', autospec=True)
    @patch('builtins.open', new_callable=mock_open)
    @patch('app.main.os.path.exists', return_value=True)
    @patch('app.main.os.makedirs')
    @patch('app.main.pd.DataFrame')
    def test_end_to_end_flow_openai_error(self, mock_dataframe_class, mock_makedirs, mock_path_exists, mock_open, mock_json_load, mock_linker, mock_content_gen):
        # Configure mock json.load to return our mock product data
        mock_json_load.return_value = self.mock_products_data

        # Configure mock linker instance
        mock_linker_instance = MagicMock()
        mock_linker.return_value = mock_linker_instance
        mock_linker_instance.generate_affiliate_link.side_effect = lambda product: f"http://testlink.com/{product['product_id']}?rf=test_affiliate_id"

        # Configure mock content generator instance to raise an exception
        mock_content_gen_instance = MagicMock()
        mock_content_gen.return_value = mock_content_gen_instance
        mock_content_gen_instance.generate_tweet_content.side_effect = Exception("Simulated OpenAI API error")

        # Mock DataFrame instance and its to_csv method
        mock_df_instance = MagicMock()
        mock_df_instance.__getitem__.return_value = mock_df_instance
        mock_dataframe_class.return_value = mock_df_instance

        # Run the main function
        main()

        # Assert that json.load and open were called for the config file
        mock_open.assert_any_call('app/products_config.json', 'r')
        mock_json_load.assert_called_once()

        # Assert that linker and content generator were initialized
        mock_linker.assert_called_once_with(affiliate_id='test_affiliate_id')
        mock_content_gen.assert_called_once_with(api_key='test_openai_key')

        # Assert that generate_affiliate_link was called for each product
        self.assertEqual(mock_linker_instance.generate_affiliate_link.call_count, len(self.mock_products_data))

        # Assert that generate_tweet_content was called for each product
        self.assertEqual(mock_content_gen_instance.generate_tweet_content.call_count, len(self.mock_products_data))

        # Assert that the outputs directory was ensured
        mock_makedirs.assert_called_once_with('outputs', exist_ok=True)

        # Assert that a DataFrame was created with the processed product data
        expected_processed_data = []
        for product in self.mock_products_data:
            expected_processed_data.append({
                'product_id': product['product_id'],
                'name': product['name'],
                'title': product['name'],
                'affiliate_link': f"http://testlink.com/{product['product_id']}?rf=test_affiliate_id",
                'tweet_text': "Error generating tweet content."
            })

        # Verify DataFrame was created with correct data
        mock_dataframe_class.assert_called_once()
        actual_processed_data = mock_dataframe_class.call_args[0][0]
        self.assertEqual(actual_processed_data, expected_processed_data)

        # Verify to_csv was called
        mock_df_instance.to_csv.assert_called_once()
        call_args, call_kwargs = mock_df_instance.to_csv.call_args
        self.assertRegex(call_args[0], r'outputs/listings_\d{8}_\d{6}.csv')
        self.assertEqual(call_kwargs.get('index'), False)

    @patch('app.main.ContentGenerator')
    @patch('app.main.ZazzleAffiliateLinker')
    @patch('app.main.json.load', autospec=True)
    @patch('builtins.open', new_callable=mock_open)
    @patch('app.main.os.path.exists', return_value=True)
    @patch('app.main.os.makedirs')
    @patch('app.main.pd.DataFrame')
    def test_end_to_end_flow_no_products(self, mock_dataframe_class, mock_makedirs, mock_path_exists, mock_open, mock_json_load, mock_linker, mock_content_gen):
        # Configure mock json.load to return an empty list
        mock_json_load.return_value = []

        # Run the main function
        main()

        # Assert that json.load and open were called for the config file
        mock_open.assert_any_call('app/products_config.json', 'r')
        mock_json_load.assert_called_once()

        # Assert that linker and content generator were NOT initialized
        mock_linker.assert_not_called()
        mock_content_gen.assert_not_called()

        # Assert that the outputs directory was ensured
        mock_makedirs.assert_called_once_with('outputs', exist_ok=True)

        # Assert that DataFrame and to_csv were NOT called
        mock_dataframe_class.assert_not_called()

    @patch('app.main.json.load', autospec=True)
    @patch('builtins.open', side_effect=FileNotFoundError("Config file not found"))
    @patch('app.main.os.path.exists', return_value=False)
    def test_end_to_end_flow_config_error(self, mock_path_exists, mock_open, mock_json_load):
        with patch('builtins.print') as mock_print:
            main()

            # Assert that open was called and raised FileNotFoundError
            mock_open.assert_called_with('app/products_config.json', 'r')

            # Assert that json.load, linker, and content generator were NOT called
            mock_json_load.assert_not_called()

    # The test_end_to_end_flow_scraper_error test is no longer relevant as scraping is removed.
    # I will remove it.
    # @patch('app.main.ZazzleProductScraper') # Removed the test below
    # def test_end_to_end_flow_scraper_error(self, mock_scraper):
    #     # Configure mock scraper instance to raise an exception during scraping
    #     mock_scraper_instance = MagicMock()
    #     mock_scraper.return_value = mock_scraper_instance
    #     mock_scraper_instance.scrape_products.side_effect = Exception("Simulated scraping error")

    #     # Patch print to capture output
    #     with patch('builtins.print') as mock_print:
    #         # Run the main function
    #         main()

    #         # Assert that the scraper was initialized and scrape_products was called
    #         mock_scraper.assert_called_once_with(max_products=3, scrape_delay=0)
    #         mock_scraper_instance.scrape_products.assert_called_once()

    #         # Assert that appropriate error messages were printed or logged (depending on main's implementation)
    #         # This part needs adjustment based on how errors are handled and reported in main.py
    #         # For now, a simple check if main finished without crashing might suffice, or check specific log messages.
    #         # Assuming for now that an error message related to scraping error would be printed/logged.
    #         # Adjust assertion based on actual logging/printing in main.py
    #         mock_print.assert_any_call("Error during scraping:", "Simulated scraping error") # Example assertion, adjust as needed

if __name__ == '__main__':
    unittest.main() 