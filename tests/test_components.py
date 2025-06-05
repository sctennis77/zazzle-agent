import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
from urllib.parse import quote

from app.affiliate_linker import (
    ZazzleAffiliateLinker,
    ZazzleAffiliateLinkerError,
    InvalidProductDataError,
    ProductData
)
from app.content_generator import ContentGenerator, generate_content_from_config


class TestComponents(unittest.TestCase):

    def setUp(self):
        # Mock necessary environment variables for tests
        self.patcher_env = patch.dict(os.environ, {
            'ZAZZLE_AFFILIATE_ID': 'test_affiliate_id',
            'OPENAI_API_KEY': 'test_openai_key'
        })
        self.patcher_env.start()
        self.addCleanup(self.patcher_env.stop)

        # Sample product data for testing
        self.test_product = {
            'title': 'Awesome T-Shirt',
            'product_id': '123456789012345678'
        }
        self.test_products = [
            {'title': 'Product A', 'product_id': 'ID_A'},
            {'title': 'Product B', 'product_id': 'ID_B'},
            {'title': 'Product C', 'product_id': 'ID_C'},
        ]

    def test_affiliate_linker_initialization(self):
        # Test successful initialization
        linker = ZazzleAffiliateLinker('test_affiliate_id')
        self.assertEqual(linker.affiliate_id, 'test_affiliate_id')

        # Test initialization with empty affiliate ID
        with self.assertRaises(ValueError):
            ZazzleAffiliateLinker('')

        # Test initialization with None affiliate ID
        with self.assertRaises(ValueError):
            ZazzleAffiliateLinker(None)

    def test_affiliate_linker_success(self):
        linker = ZazzleAffiliateLinker('test_affiliate_id')
        affiliate_link = linker.generate_affiliate_link(self.test_product)
        
        # Verify the link contains all required components
        self.assertIn('test_affiliate_id', affiliate_link)
        self.assertIn(self.test_product['product_id'], affiliate_link)
        encoded_title = quote(self.test_product['title'])
        self.assertIn(encoded_title, affiliate_link)
        self.assertIn('https://www.zazzle.com/shop', affiliate_link)

    def test_affiliate_linker_missing_data(self):
        linker = ZazzleAffiliateLinker('test_affiliate_id')
        
        # Test missing title
        incomplete_product_title_only = {'product_id': 'Only ID'}
        with self.assertRaises(InvalidProductDataError) as cm:
            linker.generate_affiliate_link(incomplete_product_title_only)
        self.assertIn('title', str(cm.exception))

        # Test missing product_id
        incomplete_product_id_only = {'title': 'Only Title'}
        with self.assertRaises(InvalidProductDataError) as cm:
            linker.generate_affiliate_link(incomplete_product_id_only)
        self.assertIn('product_id', str(cm.exception))

        # Test empty data
        with self.assertRaises(InvalidProductDataError):
            linker.generate_affiliate_link({})

    def test_affiliate_linker_batch_processing(self):
        linker = ZazzleAffiliateLinker('test_affiliate_id')
        
        # Test successful batch processing
        links = linker.generate_links_batch(self.test_products)
        self.assertEqual(len(links), len(self.test_products))
        
        for link_info in links:
            self.assertIn('affiliate_link', link_info)
            self.assertIn('test_affiliate_id', link_info['affiliate_link'])
            self.assertIn('https://www.zazzle.com/shop', link_info['affiliate_link'])

        # Test batch processing with some invalid products
        mixed_products = self.test_products + [
            {'title': 'Invalid Product'},  # Missing product_id
            {'product_id': 'Invalid ID'}   # Missing title
        ]
        
        # Should still process valid products and skip invalid ones
        links = linker.generate_links_batch(mixed_products)
        self.assertEqual(len(links), len(self.test_products))  # Only valid products processed

        # Test batch processing with all invalid products
        invalid_products = [
            {'title': 'Invalid Product'},  # Missing product_id
            {'product_id': 'Invalid ID'}   # Missing title
        ]
        
        with self.assertRaises(ZazzleAffiliateLinkerError):
            linker.generate_links_batch(invalid_products)

    def test_product_data_validation(self):
        linker = ZazzleAffiliateLinker('test_affiliate_id')
        
        # Test valid product data
        product_data = linker._validate_product_data(self.test_product)
        self.assertIsInstance(product_data, ProductData)
        self.assertEqual(product_data.title, self.test_product['title'])
        self.assertEqual(product_data.product_id, self.test_product['product_id'])
        self.assertEqual(product_data.affiliate_id, 'test_affiliate_id')

        # Test invalid product data
        with self.assertRaises(InvalidProductDataError):
            linker._validate_product_data({'title': ''})  # Empty title

        with self.assertRaises(InvalidProductDataError):
            linker._validate_product_data({'product_id': ''})  # Empty product_id

    def test_affiliate_link_construction(self):
        linker = ZazzleAffiliateLinker('test_affiliate_id')
        product = ProductData(
            title='Test Product',
            product_id='TEST123',
            affiliate_id='test_affiliate_id'
        )
        
        link = linker._construct_affiliate_link(product)
        
        # Verify link structure
        self.assertTrue(link.startswith('https://www.zazzle.com/shop?'))
        self.assertIn('rf=test_affiliate_id', link)
        self.assertIn('product_id=TEST123', link)
        self.assertIn('title=Test%20Product', link)

    @patch('app.content_generator.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data='[{"product_id": "ID_A", "name": "Product A"}, {"product_id": "ID_B", "name": "Product B"}]')
    @patch('json.load', return_value=[{"product_id": "ID_A", "name": "Product A"}, {"product_id": "ID_B", "name": "Product B"}])
    def test_content_generator_success(self, mock_json_load, mock_open, mock_openai):
        # Mock the OpenAI client and response
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        mock_client_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated tweet for Product."))]
        )

        # Call the main function that reads from the config
        generated_content = generate_content_from_config(config_file='app/products_config.json')

        # Assert that open and json.load were called
        mock_open.assert_called_with('app/products_config.json', 'r')
        mock_json_load.assert_called_once()

        # Assert that the content generator was called for each product
        self.assertEqual(len(generated_content), 2)
        self.assertIn('ID_A', generated_content)
        self.assertIn('ID_B', generated_content)
        self.assertEqual(generated_content['ID_A'], "Generated tweet for Product.")
        self.assertEqual(generated_content['ID_B'], "Generated tweet for Product.")

    @patch('app.content_generator.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data='[{"product_id": "ID_A", "name": "Product A"}]')
    @patch('json.load', return_value=[{"product_id": "ID_A", "name": "Product A"}])
    def test_content_generator_api_error(self, mock_json_load, mock_open, mock_openai):
        # Mock the OpenAI client to raise an exception
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        mock_client_instance.chat.completions.create.side_effect = Exception("Simulated API Error")

        # Call the main function that reads from the config
        generated_content = generate_content_from_config(config_file='app/products_config.json')

        # Assert that open and json.load were called
        mock_open.assert_called_with('app/products_config.json', 'r')
        mock_json_load.assert_called_once()

        # Assert that an error message is returned for the product
        self.assertEqual(len(generated_content), 1)
        self.assertIn('ID_A', generated_content)
        self.assertEqual(generated_content['ID_A'], "Error generating tweet content.")

    @patch('app.content_generator.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data='[{"product_id": "ID_A", "name": "Product A"}, {"product_id": "ID_B", "name": "Product B"}, {"product_id": "ID_C", "name": "Product C"}]')
    @patch('json.load', return_value=[{"product_id": "ID_A", "name": "Product A"}, {"product_id": "ID_B", "name": "Product B"}, {"product_id": "ID_C", "name": "Product C"}])
    def test_content_generator_multiple_products(self, mock_json_load, mock_open, mock_openai):
        # Mock the OpenAI client and response for multiple calls
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        mock_client_instance.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content="Tweet for Product A."))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Tweet for Product B."))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Tweet for Product C."))]),
        ]

        # Call the main function that reads from the config
        generated_content = generate_content_from_config(config_file='app/products_config.json')

        # Assert that open and json.load were called
        mock_open.assert_called_with('app/products_config.json', 'r')
        mock_json_load.assert_called_once()

        # Assert that content was generated for all products
        self.assertEqual(len(generated_content), 3)
        self.assertIn('ID_A', generated_content)
        self.assertIn('ID_B', generated_content)
        self.assertIn('ID_C', generated_content)
        self.assertEqual(generated_content['ID_A'], "Tweet for Product A.")
        self.assertEqual(generated_content['ID_B'], "Tweet for Product B.")
        self.assertEqual(generated_content['ID_C'], "Tweet for Product C.")

    # The original test_content_generator_batch_processing is now covered by test_content_generator_multiple_products
    # and test_content_generator_success which test the content_generator_from_config function handling multiple products.
    # I will keep the original test name but update its implementation to use the new entry point.

    @patch('app.content_generator.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data='[{"product_id": "ID_A", "name": "Product A"}, {"product_id": "ID_B", "name": "Product B"}]')
    @patch('json.load', return_value=[{"product_id": "ID_A", "name": "Product A"}, {"product_id": "ID_B", "name": "Product B"}])
    def test_content_generator_batch_processing(self, mock_json_load, mock_open, mock_openai):
        # This test now functions similarly to test_content_generator_success but keeps the original name
        # Mock the OpenAI client and response
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        mock_client_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated tweet."))]
        )

        # Call the main function that reads from the config
        generated_content = generate_content_from_config(config_file='app/products_config.json')

        # Assert that open and json.load were called
        mock_open.assert_called_with('app/products_config.json', 'r')
        mock_json_load.assert_called_once()

        # Assert that the content generator was called for each product and content is generated
        self.assertEqual(len(generated_content), 2)
        self.assertIn('ID_A', generated_content)
        self.assertIn('ID_B', generated_content)
        self.assertEqual(generated_content['ID_A'], "Generated tweet.")
        self.assertEqual(generated_content['ID_B'], "Generated tweet.")

if __name__ == '__main__':
    unittest.main() 