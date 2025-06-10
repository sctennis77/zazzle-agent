import unittest
from unittest.mock import patch, MagicMock
import os
from app.zazzle_product_designer import ZazzleProductDesigner
from urllib.parse import quote
import logging
from io import StringIO
from app.zazzle_templates import ZAZZLE_STICKER_TEMPLATE, get_product_template # Import new DTOs
import pytest
from app.models import DesignInstructions, RedditContext

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
        # Template is now obtained from design instructions, not stored in the class
        # Test that the designer can get template from design instructions
        design_instructions = DesignInstructions(
            image="https://example.com/image.jpg",
            theme="test_theme",
            template_id=self.mock_template_id_from_dto
        )
        template_id, _ = designer._get_template_config(design_instructions)
        self.assertEqual(template_id, self.mock_template_id_from_dto)

    @pytest.mark.asyncio
    @patch('requests.post')
    async def test_create_product_success(self, mock_post):
        """Test successful product creation."""
        # Mock the response from the Zazzle API
        mock_response = MagicMock()
        mock_response.json.return_value = {'product_id': '12345', 'status': 'success'}
        mock_post.return_value = mock_response

        # Call the create_product method
        result = await self.designer.create_product(self.design_instructions)

        # Assertions (adjusted to match new return value from create_product)
        self.assertIsNotNone(result)
        expected_url = f"https://www.zazzle.com/api/create/at-{self.mock_affiliate_id}?ax=linkover&pd={self.mock_template_id_from_dto}&fwd=productpage&ed=true&t_image1_url=http%3A//example.com/golf_ball_image.png&tc={ZAZZLE_STICKER_TEMPLATE.zazzle_tracking_code}"
        self.assertEqual(result['product_url'], expected_url)

    @pytest.mark.asyncio
    @patch('app.zazzle_product_designer.logger')
    async def test_create_product_error(self, mock_logger):
        """Test error handling during product creation (e.g., malformed URL components)."""
        # Simulate an error during URL quoting (e.g., malformed input)
        with patch('app.zazzle_product_designer.quote', side_effect=Exception("Quote Error")):
            designer = ZazzleProductDesigner()
            design_instructions = DesignInstructions(
                image='http://example.com/image.png',
                theme='test_theme',
                text='Test Text',
                color='Blue',
                quantity=12
            )
            result = await designer.create_product(design_instructions)
            self.assertIsNone(result)
            mock_logger.error.assert_called_with("Error creating product: Quote Error")

    @pytest.mark.asyncio
    @patch('app.zazzle_product_designer.logger')
    async def test_create_product_success_url_validation(self, mock_logger):
        designer = ZazzleProductDesigner()
        design_instructions = DesignInstructions(
            image='http://example.com/image.png',
            theme='test_theme'
        )
        result = await designer.create_product(design_instructions)

        self.assertIsNotNone(result)
        self.assertIn("https://www.zazzle.com/api/create/at-", result.product_url)
        self.assertIn(self.mock_affiliate_id, result.product_url)
        self.assertIn(self.mock_template_id_from_dto, result.product_url)

    @pytest.mark.asyncio
    @patch('app.product_designer.logger')
    @patch('app.product_designer.get_product_template', return_value=None)
    async def test_create_product_missing_template(self, mock_get_template, mock_logger):
        designer = ZazzleProductDesigner()
        product_info = {'text': 'test', 'image': 'http://a.com/i.png', 'image_iid': '123'}
        result = await designer.create_product(product_info)
        self.assertIsNone(result)
        mock_logger.error.assert_called_with("Cannot create product: Zazzle template or ZAZZLE_AFFILIATE_ID is not set.")

    @pytest.mark.asyncio
    @patch.dict(os.environ, {'ZAZZLE_AFFILIATE_ID': ''})
    @patch('app.product_designer.logger')
    async def test_create_product_missing_affiliate_id(self, mock_logger):
        designer = ZazzleProductDesigner()
        product_info = {'text': 'test', 'image': 'http://a.com/i.png', 'image_iid': '123'}
        result = await designer.create_product(product_info)
        self.assertIsNone(result)
        mock_logger.error.assert_called_with("Cannot create product: Zazzle template or ZAZZLE_AFFILIATE_ID is not set.")

    @pytest.mark.asyncio
    @patch('app.product_designer.logger')
    async def test_create_product_empty_text_and_image(self, mock_logger):
        designer = ZazzleProductDesigner()
        product_info = {
            'text': '',
            'image': '',
            'image_iid': '',
            'theme': 'test_theme'
        }
        result = await designer.create_product(product_info)
        self.assertIsNone(result)
        mock_logger.error.assert_called_once_with("Missing required image URL for field: image")

    @pytest.mark.asyncio
    @patch('app.zazzle_product_designer.logger')
    async def test_create_product_exception_handling(self, mock_logger):
        # Simulate an error during URL quoting (e.g., malformed input)
        with patch('app.zazzle_product_designer.quote', side_effect=Exception("Quote Error")):
            designer = ZazzleProductDesigner()
            design_instructions = DesignInstructions(
                image='http://example.com/image.png',
                theme='test_theme',
                text='Test Text'
            )
            result = await designer.create_product(design_instructions)
            self.assertIsNone(result)
            mock_logger.error.assert_called_with("Error creating product: Quote Error")

    @pytest.mark.asyncio
    @patch('app.zazzle_product_designer.logger')
    async def test_create_product_missing_required_fields(self, mock_logger):
        """Test product creation with missing required customizable fields."""
        designer = ZazzleProductDesigner()
        # Missing image field from design_instructions
        design_instructions = DesignInstructions(
            image='',
            theme='test_theme',
            text='Test Text'
        )
        result = await designer.create_product(design_instructions)
        self.assertIsNone(result)

    @pytest.mark.asyncio
    @patch('app.zazzle_product_designer.logger')
    async def test_create_product_invalid_url(self, mock_logger):
        """Test product creation with invalid image URL."""
        designer = ZazzleProductDesigner()
        design_instructions = DesignInstructions(
            image='invalid-url',
            theme='test_theme',
            text='Test Text'
        )
        result = await designer.create_product(design_instructions)
        self.assertIsNone(result)
        mock_logger.error.assert_called_with("Invalid image_url for field image: must start with http:// or https://")

    @pytest.mark.asyncio
    @patch('app.zazzle_product_designer.logger')
    async def test_create_product_success_with_optional_fields(self, mock_logger):
        """Test successful product creation with all optional fields."""
        designer = ZazzleProductDesigner()
        design_instructions = DesignInstructions(
            image='http://example.com/image.png',
            theme='test_theme'
        )
        result = await designer.create_product(design_instructions)
        self.assertIsNotNone(result)
        self.assertIn("https://www.zazzle.com/api/create/at-", result.product_url)
        self.assertIn(self.mock_affiliate_id, result.product_url)
        self.assertIn(self.mock_template_id_from_dto, result.product_url)

    @pytest.mark.asyncio
    async def test_create_product_with_text_color(self):
        """Test creating a product with text color customization."""
        designer = ZazzleProductDesigner()
        design_instructions = DesignInstructions(
            image='https://example.com/image.jpg',
            color='Red'
        )
        
        result = await designer.create_product(design_instructions)
        assert result is not None
        assert result.product_url is not None

    @pytest.mark.asyncio
    async def test_create_product_with_contrast_text_color(self):
        """Test creating a product with contrast-based text color selection."""
        designer = ZazzleProductDesigner()
        design_instructions = DesignInstructions(
            image='https://example.com/dark-image.jpg'
        )
        
        result = await designer.create_product(design_instructions)
        assert result is not None
        assert result.product_url is not None

    @pytest.mark.asyncio
    async def test_create_product_with_thematic_text_color(self):
        """Test creating a product with thematic text color selection."""
        designer = ZazzleProductDesigner()
        design_instructions = DesignInstructions(
            image='https://example.com/image.jpg'
        )
        
        result = await designer.create_product(design_instructions)
        assert result is not None
        assert result.product_url is not None

    @pytest.mark.asyncio
    async def test_create_product_with_invalid_text_color(self):
        """Test creating a product with an invalid text color."""
        designer = ZazzleProductDesigner()
        design_instructions = DesignInstructions(
            image='https://example.com/image.jpg',
            color='InvalidColor'
        )
        
        result = await designer.create_product(design_instructions)
        assert result is not None
        assert result.product_url is not None

    @pytest.mark.asyncio
    async def test_create_product_without_text_color(self):
        """Test creating a product without specifying text color (should default to black)."""
        designer = ZazzleProductDesigner()
        design_instructions = DesignInstructions(
            image='https://example.com/image.jpg'
        )
        
        result = await designer.create_product(design_instructions)
        assert result is not None
        assert result.product_url is not None

if __name__ == '__main__':
    unittest.main() 