import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
from urllib.parse import quote

from app.affiliate_linker import ZazzleAffiliateLinker
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

    def test_affiliate_linker_success(self):
        linker = ZazzleAffiliateLinker('test_affiliate_id')
        affiliate_link = linker.generate_affiliate_link(self.test_product)
        self.assertIn('test_affiliate_id', affiliate_link)
        self.assertIn(self.test_product['product_id'], affiliate_link)
        encoded_title = quote(self.test_product['title'])
        self.assertIn(encoded_title, affiliate_link)
        self.assertIn('https://www.zazzle.com/', affiliate_link)

    def test_affiliate_linker_missing_data(self):
        linker = ZazzleAffiliateLinker('test_affiliate_id')
        incomplete_product_title_only = {'title': 'Only Title'}
        incomplete_product_id_only = {'product_id': 'Only ID'}

        # Check that KeyError is raised when 'product_id' is missing
        with self.assertRaises(KeyError) as cm:
            linker.generate_affiliate_link(incomplete_product_title_only)
        self.assertIn('product_id', str(cm.exception))

        # Check that KeyError is raised when 'title' is missing
        with self.assertRaises(KeyError) as cm:
            linker.generate_affiliate_link(incomplete_product_id_only)
        self.assertIn('title', str(cm.exception))


    def test_affiliate_linker_batch_processing(self):
        linker = ZazzleAffiliateLinker('test_affiliate_id')
        # Correct the method name from generate_affiliate_links to generate_links_batch
        links = linker.generate_links_batch(self.test_products)
        self.assertEqual(len(links), len(self.test_products))
        for link_info in links:
            self.assertIn('affiliate_link', link_info)
            self.assertIn('test_affiliate_id', link_info['affiliate_link'])
            self.assertIn('https://www.zazzle.com/', link_info['affiliate_link'])

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