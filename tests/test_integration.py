import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from app.main import main
from app.product_scraper import ZazzleProductScraper
from app.affiliate_linker import ZazzleAffiliateLinker
from app.content_generator import ContentGenerator

class TestIntegration(unittest.TestCase):
    def setUp(self):
        # Create test outputs directory
        os.makedirs('outputs', exist_ok=True)
        
        # Sample test data
        self.mock_products = [
            {
                'title': 'Test Product 1',
                'product_id': '123456'
            },
            {
                'title': 'Test Product 2',
                'product_id': '789012'
            }
        ]
        
        # Mock OpenAI response
        self.mock_openai_response = MagicMock()
        self.mock_openai_response.choices = [
            MagicMock(message=MagicMock(content="Amazing product! #shopping #gifts"))
        ]

    @patch('app.product_scraper.webdriver.Chrome')
    @patch('app.product_scraper.ZazzleProductScraper.scrape_bestsellers')
    @patch('openai.ChatCompletion.create')
    def test_end_to_end_flow(self, mock_openai, mock_scraper, mock_driver):
        # Mock the Chrome driver
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance
        
        # Mock the scraper to return test products
        mock_scraper.return_value = self.mock_products
        
        # Mock OpenAI response
        mock_openai.return_value = self.mock_openai_response
        
        # Run the main function
        main()
        
        # Verify the output file exists
        output_files = [f for f in os.listdir('outputs') if f.startswith('listings_')]
        self.assertTrue(len(output_files) > 0)
        
        # Read the most recent output file
        latest_file = sorted(output_files)[-1]
        df = pd.read_csv(f'outputs/{latest_file}')
        
        # Verify the structure of the output
        self.assertIn('title', df.columns)
        self.assertIn('affiliate_link', df.columns)
        self.assertIn('tweet_text', df.columns)
        
        # Verify the content
        self.assertEqual(len(df), len(self.mock_products))
        self.assertTrue(all('238627313417608652' in link for link in df['affiliate_link']))
        self.assertTrue(all('#shopping' in tweet for tweet in df['tweet_text']))

    def tearDown(self):
        # Clean up test output files
        for file in os.listdir('outputs'):
            if file.startswith('listings_'):
                os.remove(os.path.join('outputs', file))

if __name__ == '__main__':
    unittest.main() 