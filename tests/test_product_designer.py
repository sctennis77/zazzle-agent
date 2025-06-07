import unittest
from unittest.mock import patch, MagicMock
import os
from app.product_designer import ZazzleProductDesigner
from urllib.parse import quote
import logging
from io import StringIO

class TestZazzleProductDesigner(unittest.TestCase):
    """Test cases for the Zazzle Product Designer Agent."""

    def setUp(self):
        """Set up the test environment."""
        # Mock environment variables for ZazzleProductDesigner
        self.patcher_env = patch.dict(os.environ, {
            'ZAZZLE_AFFILIATE_ID': 'test_affiliate_id',
            'ZAZZLE_TEMPLATE_ID': 'test_template_id',
            'ZAZZLE_TRACKING_CODE': 'test_tracking_code'
        })
        self.patcher_env.start()
        self.addCleanup(self.patcher_env.stop)

        # Set up log capture
        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        # Get the logger for the app module to capture its output
        app_logger = logging.getLogger('app')
        app_logger.addHandler(self.handler)
        app_logger.setLevel(logging.INFO) # Set level to INFO to capture info and error logs
        self.addCleanup(lambda: app_logger.removeHandler(self.handler))

        self.designer = ZazzleProductDesigner()
        self.design_instructions = {
            'text': 'Golf Ball Design',
            'image_url': 'http://example.com/golf_ball_image.png',
            'image_iid': '1234567890',
            'theme': 'golf',
            'color': 'white',
            'quantity': 12
        }
        self.mock_affiliate_id = "test_affiliate_id"
        self.mock_template_id = "test_template_id"
        self.mock_tracking_code = "test_tracking_code"
        
        # Patch environment variables
        self.env_patcher = patch.dict('os.environ', {
            'ZAZZLE_AFFILIATE_ID': self.mock_affiliate_id,
            'ZAZZLE_TEMPLATE_ID': self.mock_template_id,
            'ZAZZLE_TRACKING_CODE': self.mock_tracking_code
        })
        self.env_patcher.start()

    def tearDown(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()

    def test_initialization_loads_env_vars(self):
        designer = ZazzleProductDesigner()
        self.assertEqual(designer.affiliate_id, self.mock_affiliate_id)
        self.assertEqual(designer.template_id, self.mock_template_id)
        self.assertEqual(designer.tracking_code, self.mock_tracking_code)

    @patch('requests.post')
    def test_create_product_success(self, mock_post):
        """Test successful product creation."""
        # Mock the response from the Zazzle API
        mock_response = MagicMock()
        mock_response.json.return_value = {'product_id': '12345', 'status': 'success'}
        mock_post.return_value = mock_response

        # Call the create_product method
        result = self.designer.create_product(self.design_instructions)

        # Assertions
        self.assertEqual(result, {'product_id': '12345', 'status': 'success'})
        mock_post.assert_called_once()

    @patch('app.product_designer.logger')
    def test_create_product_error(self, mock_logger):
        """Test error handling during product creation (e.g., malformed URL components)."""
        # Simulate an error during URL quoting (e.g., malformed input)
        with patch('app.product_designer.quote', side_effect=Exception("Quote Error")):
            designer = ZazzleProductDesigner()
            product_info = {
                'text': 'Test Text',
                'image_url': 'http://example.com/image.png',
                'image_iid': 'test_image_iid',
                'theme': 'test_theme'
            }
            result = designer.create_product(product_info)
            self.assertIsNone(result)
            mock_logger.error.assert_called_with("Error creating product: Quote Error")

    @patch('app.product_designer.logger')
    def test_create_product_success(self, mock_logger):
        designer = ZazzleProductDesigner()
        product_info = {
            'text': 'Test Text',
            'image_url': 'http://example.com/image.png',
            'image_iid': 'test_image_iid',
            'theme': 'test_theme'
        }
        result = designer.create_product(product_info)

        self.assertIsNotNone(result)
        self.assertIn("https://www.zazzle.com/api/create/at-", result['product_url'])
        self.assertIn(self.mock_affiliate_id, result['product_url'])
        self.assertIn(self.mock_template_id, result['product_url'])
        # Assert that the URL-encoded text is in the product URL
        self.assertIn(quote(product_info['text']), result['product_url'])
        mock_logger.info.assert_any_call(f"Successfully generated product URL: {result['product_url']}")

    @patch('app.product_designer.logger')
    def test_create_product_missing_template_id(self, mock_logger):
        with patch.dict(os.environ, {'ZAZZLE_TEMPLATE_ID': ''}):
            designer = ZazzleProductDesigner()
            result = designer.create_product({'text': 'test'})
            self.assertIsNone(result)
            mock_logger.error.assert_called_with("Cannot create product: ZAZZLE_TEMPLATE_ID or ZAZZLE_AFFILIATE_ID is not set.")

    @patch('app.product_designer.logger')
    def test_create_product_missing_affiliate_id(self, mock_logger):
        with patch.dict(os.environ, {'ZAZZLE_AFFILIATE_ID': ''}):
            designer = ZazzleProductDesigner()
            result = designer.create_product({'text': 'test'})
            self.assertIsNone(result)
            mock_logger.error.assert_called_with("Cannot create product: ZAZZLE_TEMPLATE_ID or ZAZZLE_AFFILIATE_ID is not set.")

    @patch('app.product_designer.logger')
    def test_create_product_empty_text_and_image(self, mock_logger):
        designer = ZazzleProductDesigner()
        product_info = {'text': '', 'image_url': '', 'image_iid': '', 'theme': 'test_theme'}
        result = designer.create_product(product_info)
        self.assertIsNone(result)

    @patch('app.product_designer.logger')
    def test_create_product_exception_handling(self, mock_logger):
        # Simulate an error during URL quoting (e.g., malformed input)
        with patch('app.product_designer.quote', side_effect=Exception("Quote Error")):
            designer = ZazzleProductDesigner()
            product_info = {'text': 'Test Text', 'image_url': 'http://example.com/image.png', 'image_iid': 'test_image_iid', 'theme': 'test_theme'}
            result = designer.create_product(product_info)
            self.assertIsNone(result)
            mock_logger.error.assert_called_with("Error creating product: Quote Error")

    def test_create_product_missing_required_fields(self):
        """Test product creation with missing required fields."""
        designer = ZazzleProductDesigner()
        # Missing text field
        product_info = {
            'image_url': 'http://example.com/image.png',
            'image_iid': 'test_image_iid',
            'theme': 'test_theme'
        }
        result = designer.create_product(product_info)
        self.assertIsNone(result)

    def test_create_product_invalid_url(self):
        """Test product creation with invalid image URL."""
        designer = ZazzleProductDesigner()
        product_info = {
            'text': 'Test Text',
            'image_url': 'invalid-url',
            'image_iid': 'test_image_iid',
            'theme': 'test_theme'
        }
        result = designer.create_product(product_info)
        self.assertIsNone(result)

    def test_create_product_success_with_optional_fields(self):
        """Test successful product creation with all optional fields."""
        designer = ZazzleProductDesigner()
        product_info = {
            'text': 'Test Text',
            'image_url': 'http://example.com/image.png',
            'image_iid': 'test_image_iid',
            'theme': 'test_theme',
            'color': 'Blue',
            'quantity': 12
        }
        result = designer.create_product(product_info)
        self.assertIsNotNone(result)
        self.assertIn("https://www.zazzle.com/api/create/at-", result['product_url'])
        self.assertIn(self.mock_affiliate_id, result['product_url'])
        self.assertIn(self.mock_template_id, result['product_url'])
        self.assertIn(quote(product_info['text']), result['product_url'])
        self.assertIn(quote(product_info['color']), result['product_url'])
        self.assertIn(str(product_info['quantity']), result['product_url'])

if __name__ == '__main__':
    unittest.main() 