import unittest
from unittest.mock import patch, MagicMock
import os
from app.product_designer import ZazzleProductDesigner
from urllib.parse import quote
import logging
from io import StringIO
from app.zazzle_templates import ZAZZLE_STICKER_TEMPLATE, get_product_template # Import new DTOs

class TestZazzleProductDesigner(unittest.TestCase):
    """Test cases for the Zazzle Product Designer Agent."""

    def setUp(self):
        """Set up the test environment."""
        # Mock environment variables for ZazzleProductDesigner
        self.patcher_env = patch.dict(os.environ, {
            'ZAZZLE_AFFILIATE_ID': 'test_affiliate_id',
            # ZAZZLE_TEMPLATE_ID is now loaded from DTO, no longer mocked as env var
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

        # Initialize designer after environment variables are set
        self.designer = ZazzleProductDesigner()
        
        # Updated design_instructions to match the new DTO structure for customizable_fields
        self.design_instructions = {
            'text': 'Golf Ball Design',
            'image': 'http://example.com/golf_ball_image.png',
            'image_iid': '1234567890',
            'theme': 'golf',
            'color': 'white',
            'quantity': 12
        }
        self.mock_affiliate_id = "test_affiliate_id"
        # template_id is now from DTO, not directly from env var
        self.mock_template_id_from_dto = ZAZZLE_STICKER_TEMPLATE.zazzle_template_id
        self.mock_tracking_code = "test_tracking_code"
        
        # Patch environment variables for specific tests that still rely on it
        self.env_patcher = patch.dict('os.environ', {
            'ZAZZLE_AFFILIATE_ID': self.mock_affiliate_id,
            'ZAZZLE_TEMPLATE_ID': self.mock_template_id_from_dto, # Use DTO value here for mocks
            'ZAZZLE_TRACKING_CODE': self.mock_tracking_code
        })
        self.env_patcher.start()

    def tearDown(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()

    def test_initialization_loads_env_vars(self):
        designer = ZazzleProductDesigner()
        self.assertEqual(designer.affiliate_id, self.mock_affiliate_id)
        # Assert against the template ID loaded from the DTO, not a mocked env var
        self.assertEqual(designer.template.zazzle_template_id, self.mock_template_id_from_dto)
        # Tracking code is now from the DTO if a template is loaded
        self.assertEqual(designer.tracking_code, ZAZZLE_STICKER_TEMPLATE.zazzle_tracking_code)

    @patch('requests.post')
    def test_create_product_success(self, mock_post):
        """Test successful product creation."""
        # Mock the response from the Zazzle API
        mock_response = MagicMock()
        mock_response.json.return_value = {'product_id': '12345', 'status': 'success'}
        mock_post.return_value = mock_response

        # Call the create_product method
        result = self.designer.create_product(self.design_instructions)

        # Assertions (adjusted to match new return value from create_product)
        self.assertIsNotNone(result)
        # Correct the expected tracking code to match the DTO value
        expected_url = f"https://www.zazzle.com/api/create/at-{self.mock_affiliate_id}?ax=linkover&pd={self.mock_template_id_from_dto}&fwd=productpage&ed=true&t_text1_txt=Golf%20Ball%20Design&t_image1_iid=1234567890&color=white&quantity=12&tc={ZAZZLE_STICKER_TEMPLATE.zazzle_tracking_code}"
        self.assertEqual(result['product_url'], expected_url)
        mock_post.assert_not_called() # No external API call is made in current create_product

    @patch('app.product_designer.logger')
    def test_create_product_error(self, mock_logger):
        """Test error handling during product creation (e.g., malformed URL components)."""
        # Simulate an error during URL quoting (e.g., malformed input)
        with patch('app.product_designer.quote', side_effect=Exception("Quote Error")):
            designer = ZazzleProductDesigner()
            product_info = {
                'text': 'Test Text',
                'image': 'http://example.com/image.png',
                'image_iid': 'test_image_iid',
                'theme': 'test_theme',
                'color': 'Blue',
                'quantity': 12
            }
            result = designer.create_product(product_info)
            self.assertIsNone(result)
            mock_logger.error.assert_called_with("Error creating product: Quote Error")

    @patch('app.product_designer.logger')
    def test_create_product_success_url_validation(self, mock_logger):
        designer = ZazzleProductDesigner()
        product_info = {
            'text': 'Test Text',
            'image': 'http://example.com/image.png',
            'image_iid': 'test_image_iid',
            'theme': 'test_theme'
        }
        result = designer.create_product(product_info)

        self.assertIsNotNone(result)
        self.assertIn("https://www.zazzle.com/api/create/at-", result['product_url'])
        self.assertIn(self.mock_affiliate_id, result['product_url'])
        self.assertIn(self.mock_template_id_from_dto, result['product_url'])
        # Assert that the URL-encoded text is in the product URL
        self.assertIn(quote(product_info['text']), result['product_url'])
        mock_logger.info.assert_any_call(f"Successfully generated product URL: {result['product_url']}")

    @patch('app.product_designer.logger')
    @patch('app.product_designer.get_product_template', return_value=None) # Patch get_product_template where ProductDesigner looks for it
    def test_create_product_missing_template(self, mock_get_template, mock_logger):
        designer = ZazzleProductDesigner()
        product_info = {'text': 'test', 'image': 'http://a.com/i.png', 'image_iid': '123'}
        result = designer.create_product(product_info)
        self.assertIsNone(result)
        # Assert that the error from create_product when template is missing is logged
        mock_logger.error.assert_called_with("Cannot create product: Zazzle template or ZAZZLE_AFFILIATE_ID is not set.")

    @patch.dict(os.environ, {'ZAZZLE_AFFILIATE_ID': ''})
    @patch('app.product_designer.logger')
    def test_create_product_missing_affiliate_id(self, mock_logger):
        designer = ZazzleProductDesigner()
        product_info = {'text': 'test', 'image': 'http://a.com/i.png', 'image_iid': '123'}
        result = designer.create_product(product_info)
        self.assertIsNone(result)
        mock_logger.error.assert_called_with("Cannot create product: Zazzle template or ZAZZLE_AFFILIATE_ID is not set.")

    @patch('app.product_designer.logger')
    def test_create_product_empty_text_and_image(self, mock_logger):
        designer = ZazzleProductDesigner()
        # Based on current DTO, only text and image are customizable. Other fields are derived.
        product_info = {
            'text': '',
            'image': '',
            'image_iid': '',
            'theme': 'test_theme' # Theme is still expected from reddit_agent
        }
        result = designer.create_product(product_info)
        self.assertIsNone(result)
        # Expecting error for missing text and image URL/IID due to validation in create_product
        mock_logger.error.assert_called_once_with("Missing required text field: text")
        # Only assert the first error encountered, as the function returns early
        # mock_logger.error.assert_any_call("Missing required image URL or IID for field: image")

    @patch('app.product_designer.logger')
    def test_create_product_exception_handling(self, mock_logger):
        # Simulate an error during URL quoting (e.g., malformed input)
        with patch('app.product_designer.quote', side_effect=Exception("Quote Error")):
            designer = ZazzleProductDesigner()
            product_info = {'text': 'Test Text', 'image': 'http://example.com/image.png', 'image_iid': 'test_image_iid', 'theme': 'test_theme'}
            result = designer.create_product(product_info)
            self.assertIsNone(result)
            mock_logger.error.assert_called_with("Error creating product: Quote Error")

    @patch('app.product_designer.logger')
    def test_create_product_missing_required_fields(self, mock_logger):
        """Test product creation with missing required customizable fields."""
        designer = ZazzleProductDesigner()
        # Missing text field from product_info
        product_info = {
            'image': 'http://example.com/image.png',
            'image_iid': 'test_image_iid',
            'theme': 'test_theme'
        }
        result = designer.create_product(product_info)
        self.assertIsNone(result)
        mock_logger.error.assert_called_with("Missing required text field: text")

    @patch('app.product_designer.logger')
    def test_create_product_invalid_url(self, mock_logger):
        """Test product creation with invalid image URL."""
        designer = ZazzleProductDesigner()
        product_info = {
            'text': 'Test Text',
            'image': 'invalid-url',
            'image_iid': 'test_image_iid',
            'theme': 'test_theme'
        }
        result = designer.create_product(product_info)
        self.assertIsNone(result)
        mock_logger.error.assert_called_with("Invalid image_url for field image: must start with http:// or https://")

    @patch('app.product_designer.logger')
    def test_create_product_success_with_optional_fields(self, mock_logger):
        """Test successful product creation with all optional fields."""
        designer = ZazzleProductDesigner()
        product_info = {
            'text': 'Test Text',
            'image': 'http://example.com/image.png',
            'image_iid': 'test_image_iid',
            'theme': 'test_theme',
            'color': 'Blue',
            'quantity': 12
        }
        result = designer.create_product(product_info)
        self.assertIsNotNone(result)
        self.assertIn("https://www.zazzle.com/api/create/at-", result['product_url'])
        self.assertIn(self.mock_affiliate_id, result['product_url'])
        self.assertIn(self.mock_template_id_from_dto, result['product_url'])
        self.assertIn(quote(product_info['text']), result['product_url'])
        self.assertIn(quote(product_info['color']), result['product_url'])
        self.assertIn(str(product_info['quantity']), result['product_url'])
        # Correct the expected tracking code to match the DTO value
        expected_url_part = f"tc={ZAZZLE_STICKER_TEMPLATE.zazzle_tracking_code}"
        self.assertIn(expected_url_part, result['product_url'])
        mock_logger.info.assert_any_call(f"Successfully generated product URL: {result['product_url']}")

if __name__ == '__main__':
    unittest.main() 