import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import quote
from app.product_scraper import ZazzleProductScraper
from app.affiliate_linker import ZazzleAffiliateLinker
from app.content_generator import ContentGenerator

class TestComponents(unittest.TestCase):
    def setUp(self):
        self.affiliate_id = "238627313417608652"
        self.test_product = {
            'title': 'Test Product',
            'product_id': '123456'
        }

    @patch('app.product_scraper.webdriver.Chrome')
    def test_product_scraper(self, mock_driver):
        # Mock the Chrome driver
        mock_driver_instance = MagicMock()
        mock_driver.return_value = mock_driver_instance
        
        # Mock the page source
        mock_driver_instance.page_source = """
        <div class="product-card" data-product-id="123456">
            <h3 class="product-title">Test Product</h3>
        </div>
        """
        
        scraper = ZazzleProductScraper(delay=0)
        products = scraper.scrape_bestsellers(max_products=1)
        
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['title'], 'Test Product')
        self.assertEqual(products[0]['product_id'], '123456')

    def test_affiliate_linker(self):
        linker = ZazzleAffiliateLinker(affiliate_id=self.affiliate_id)
        affiliate_link = linker.generate_affiliate_link(self.test_product)
        
        # URL encode the title for comparison
        encoded_title = quote(self.test_product['title'])
        
        self.assertIn(self.affiliate_id, affiliate_link)
        self.assertIn(self.test_product['product_id'], affiliate_link)
        self.assertIn(encoded_title, affiliate_link)

    @patch('openai.ChatCompletion.create')
    def test_content_generator(self, mock_openai):
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Amazing product! #shopping #gifts"))
        ]
        mock_openai.return_value = mock_response
        
        content_gen = ContentGenerator()
        tweet_text = content_gen.generate_tweet(self.test_product)
        
        self.assertIsInstance(tweet_text, str)
        self.assertTrue(len(tweet_text) > 0)
        self.assertTrue('#' in tweet_text)

if __name__ == '__main__':
    unittest.main() 