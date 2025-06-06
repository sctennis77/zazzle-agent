import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
from urllib.parse import quote

from app.affiliate_linker import (
    ZazzleAffiliateLinker,
    ZazzleAffiliateLinkerError,
    InvalidProductDataError
)
from app.content_generator import ContentGenerator, generate_content_from_config
from app.models import Product, ContentType


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

        self.affiliate_id = "test_affiliate_id"
        self.openai_api_key = "test_openai_api_key"
        self.linker = ZazzleAffiliateLinker(self.affiliate_id)
        self.content_gen = ContentGenerator(self.openai_api_key)

    def test_affiliate_linker_initialization(self):
        # Test successful initialization
        linker = ZazzleAffiliateLinker(affiliate_id="test_id")
        self.assertEqual(linker.affiliate_id, "test_id")

        # Test initialization with empty affiliate ID
        with self.assertRaises(ValueError):
            ZazzleAffiliateLinker(affiliate_id="")

        # Test initialization with None affiliate ID
        with self.assertRaises(ValueError):
            ZazzleAffiliateLinker(affiliate_id=None)

    def test_affiliate_linker_success(self):
        product = Product(product_id="ID_A", name="Product A")
        affiliate_link = self.linker.generate_affiliate_link(product.product_id, product.name)
        self.assertIn(self.affiliate_id, affiliate_link)
        # The product ID is now part of the path, not a query parameter
        self.assertIn(f"/product/{product.product_id}", affiliate_link)
        # Ensure the base URL is correct
        self.assertTrue(affiliate_link.startswith("https://www.zazzle.com/product/"))

    def test_affiliate_linker_missing_data(self):
        # Test missing product ID
        product_no_id = Product(product_id="", name="Product Name")
        with self.assertRaises(InvalidProductDataError) as cm:
            # Need to call the method that performs validation
            self.linker.generate_affiliate_link(product_no_id.product_id, product_no_id.name)
        self.assertIn("Product ID is required", str(cm.exception)) # Corrected expected message

        # Test missing product name - name is now required by the linker for valid link generation
        product_no_name = Product(product_id="ID_A", name="")
        with self.assertRaises(InvalidProductDataError) as cm:
             self.linker.generate_affiliate_link(product_no_name.product_id, product_no_name.name)
        self.assertIn("Product name is required", str(cm.exception)) # Corrected expected message

    def test_affiliate_linker_batch_processing(self):
        products = [
            Product(product_id="ID_A", name="Product A"), # Valid
            Product(product_id="", name="Invalid Product"), # Invalid product with missing ID
            Product(product_id="ID_C", name="Product C"), # Valid
            Product(product_id="ID_D", name="") # Invalid product with missing name
        ]

        processed_products = self.linker.generate_links_batch(products)

        self.assertEqual(len(processed_products), 4) # Ensure all products are processed

        # Check the results for each product individually
        self.assertIsNotNone(processed_products[0].affiliate_link) # Valid product A
        self.assertIsNone(processed_products[1].affiliate_link) # Invalid product (missing ID)
        self.assertIsNotNone(processed_products[2].affiliate_link) # Valid product C
        self.assertIsNone(processed_products[3].affiliate_link) # Invalid product (missing name)

        # You might also want to check that the generated links are correct for valid products
        self.assertIn("ID_A", processed_products[0].affiliate_link)
        self.assertIn(self.affiliate_id, processed_products[0].affiliate_link)
        self.assertIn("ID_C", processed_products[2].affiliate_link)
        self.assertIn(self.affiliate_id, processed_products[2].affiliate_link)

        # Check logs for errors on invalid products (assuming logging is configured)
        # You might need to capture logs in your test setup to assert specific log messages

    def test_content_generator_success(self):
        # Mock OpenAI API to return a successful response
        with patch('app.content_generator.openai.OpenAI') as MockOpenAI:
            mock_client_instance = MockOpenAI.return_value
            mock_client_instance.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(content="Test content"))]
            )

            content_gen = ContentGenerator()
            product_name = "Test Product"
            content = content_gen.generate_tweet_content(product_name)

            # Assert that the correct content was returned
            self.assertEqual(content, "Test content")

    def test_content_generator_api_error(self):
        # Mock OpenAI API to raise an exception
        with patch('app.content_generator.openai.OpenAI') as MockOpenAI:
            mock_client_instance = MockOpenAI.return_value
            mock_client_instance.chat.completions.create.side_effect = Exception("API Error")

            content_gen = ContentGenerator()
            product_name = "Test Product"
            # The generate_tweet_content function catches the exception and returns an error message
            content = content_gen.generate_tweet_content(product_name)

            # Assert that an error message is returned
            self.assertEqual(content, "Error generating tweet content")

    def test_content_generator_multiple_products(self):
        # Mock OpenAI API to return consistent responses
        with patch('app.content_generator.openai.OpenAI') as MockOpenAI:
            mock_client_instance = MockOpenAI.return_value
            mock_client_instance.chat.completions.create.side_effect = [
                Mock(choices=[Mock(message=Mock(content="Content for Product 1"))]),
                Mock(choices=[Mock(message=Mock(content="Content for Product 2"))]),
            ]

            content_gen = ContentGenerator()
            content1 = content_gen.generate_tweet_content("Product 1")
            content2 = content_gen.generate_tweet_content("Product 2")

            # Assert that content was generated for both products
            self.assertEqual(content1, "Content for Product 1")
            self.assertEqual(content2, "Content for Product 2")

    def test_content_generator_batch_processing(self):
        products = [
            Product(product_id="ID_A", name="Product A"),
            Product(product_id="ID_B", name="Product B"),
            Product(product_id="ID_C", name="Product C"),
        ]

        # Mock OpenAI API to return consistent responses
        with patch('app.content_generator.openai.OpenAI') as MockOpenAI:
            mock_client_instance = MockOpenAI.return_value
            mock_client_instance.chat.completions.create.side_effect = [
                Mock(choices=[Mock(message=Mock(content="Content for Product A"))]),
                Mock(choices=[Mock(message=Mock(content="Content for Product B"))]),
                Mock(choices=[Mock(message=Mock(content="Content for Product C"))]),
            ]

            content_gen = ContentGenerator()
            processed_products = content_gen.generate_content_batch(products)

            # Check that all products have content and content_type
            for product in processed_products:
                self.assertIsNotNone(product.content)
                self.assertEqual(product.content_type, ContentType.TWEET)
                self.assertTrue(product.content.startswith("Content for"))

    def test_product_data_validation(self):
        # Test valid product data
        valid_product = Product(product_id="ID_A", name="Product A")
        valid_product_no_name = Product(product_id="ID_B", name="")
        valid_product_no_id = Product(product_id="", name="Product C")

        # Validation for missing ID or name happens in linker.generate_affiliate_link
        # These assertions were moved to test_affiliate_linker_missing_data

    @patch('app.content_generator.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data='[{"product_id": "ID_A", "name": "Product A"}, {"product_id": "ID_B", "name": "Product B"}]')
    @patch('json.load', return_value=[{"product_id": "ID_A", "name": "Product A"}, {"product_id": "ID_B", "name": "Product B"}])
    def test_content_generator_success(self, mock_json_load, mock_open, mock_openai):
        # Mock the OpenAI client and response
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        mock_client_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated content for Product."))]
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
        self.assertEqual(generated_content['ID_A'], "Generated content for Product.")
        self.assertEqual(generated_content['ID_B'], "Generated content for Product.")

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
        self.assertEqual(generated_content['ID_A'], "Error generating tweet content")

    @patch('app.content_generator.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data='[{"product_id": "ID_A", "name": "Product A"}, {"product_id": "ID_B", "name": "Product B"}, {"product_id": "ID_C", "name": "Product C"}]')
    @patch('json.load', return_value=[{"product_id": "ID_A", "name": "Product A"}, {"product_id": "ID_B", "name": "Product B"}, {"product_id": "ID_C", "name": "Product C"}])
    def test_content_generator_multiple_products(self, mock_json_load, mock_open, mock_openai):
        # Mock the OpenAI client and response for multiple calls
        mock_client_instance = MagicMock()
        mock_openai.return_value = mock_client_instance
        mock_client_instance.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content="Content for Product A."))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Content for Product B."))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content="Content for Product C."))]),
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
        self.assertEqual(generated_content['ID_A'], "Content for Product A.")
        self.assertEqual(generated_content['ID_B'], "Content for Product B.")
        self.assertEqual(generated_content['ID_C'], "Content for Product C.")

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
            choices=[MagicMock(message=MagicMock(content="Generated content."))]
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
        self.assertEqual(generated_content['ID_A'], "Generated content.")
        self.assertEqual(generated_content['ID_B'], "Generated content.")

if __name__ == '__main__':
    unittest.main() 