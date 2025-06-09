import unittest
from unittest.mock import patch, MagicMock, AsyncMock, ANY
import os
import pytest
import base64
from typing import Tuple, Generator
from unittest import IsolatedAsyncioTestCase
from app.image_generator import ImageGenerator, IMAGE_GENERATION_BASE_PROMPTS

# Module-level fixture to patch openai.OpenAI for all async tests
@pytest.fixture(autouse=True, scope="module")
def patch_openai():
    with patch('openai.OpenAI') as mock_openai:
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance
        yield mock_openai, mock_openai_instance

@pytest.fixture(scope="module")
def mock_imgur_responses() -> Tuple[str, str]:
    """Fixture providing mock Imgur responses."""
    return 'https://imgur.com/test.jpg', 'outputs/images/test.png'

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    patcher = patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'})
    patcher.start()
    yield
    patcher.stop()

class TestImageGenerator(unittest.TestCase):
    """Test cases for the ImageGenerator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock OpenAI client
        self.mock_openai = patch('openai.OpenAI').start()
        self.mock_openai_instance = MagicMock()
        self.mock_openai.return_value = self.mock_openai_instance
        
        # Mock ImgurClient
        self.mock_imgur = patch('app.clients.imgur_client.ImgurClient').start()
        self.mock_imgur_instance = MagicMock()
        self.mock_imgur.return_value = self.mock_imgur_instance
        
        self.image_generator = ImageGenerator()

    def tearDown(self):
        """Clean up test fixtures."""
        patch.stopall()

    def test_initialization(self):
        """Test ImageGenerator initialization."""
        self.assertIsNotNone(self.image_generator)
        self.assertIsNotNone(self.image_generator.client)
        self.assertIsNotNone(self.image_generator.imgur_client)

    def test_initialization_missing_api_key(self):
        """Test initialization fails when OPENAI_API_KEY is not set."""
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError):
                ImageGenerator()

@pytest.mark.asyncio
class TestImageGeneratorAsync(IsolatedAsyncioTestCase):
    """Test cases for the ImageGenerator class."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.image_generator = ImageGenerator(model="dall-e-2")
        self.mock_openai_instance = MagicMock()
        self.image_generator.client = self.mock_openai_instance
        
        # Setup Imgur mocks
        self.mock_imgur_upload = patch('app.clients.imgur_client.ImgurClient.upload_image', 
                                     return_value=("https://i.imgur.com/test.png", "test.png")).start()
        self.mock_imgur_save = patch('app.clients.imgur_client.ImgurClient.save_image_locally', 
                                   return_value="test.png").start()
        
    def _verify_openai_call(self, prompt: str, size: str = "256x256"):
        """Verify OpenAI API call with expected parameters."""
        expected_prompt = f"{IMAGE_GENERATION_BASE_PROMPTS['dall-e-2']} {prompt}"
        self.mock_openai_instance.images.generate.assert_called_once_with(
            model="dall-e-2",
            prompt=expected_prompt,
            size=size,
            n=1,
            response_format="b64_json"
        )
        
    def _verify_imgur_calls(self, image_data: bytes, expected_filename=None):
        """Verify Imgur API calls."""
        self.mock_imgur_save.assert_called_once_with(image_data, ANY, subdirectory="generated_products")
        self.mock_imgur_upload.assert_called_once_with(ANY)
        
    @patch('httpx.AsyncClient')
    async def test_generate_image_success(self, mock_httpx):
        """Test successful image generation and storage."""
        # Mock OpenAI response
        self.mock_openai_instance.images.generate.return_value = MagicMock(
            data=[MagicMock(b64_json='Zm9vYmFy')]
        )
        
        # Test image generation
        imgur_url, local_path = await self.image_generator.generate_image('test prompt')
        
        # Verify calls
        self._verify_openai_call('test prompt')
        self._verify_imgur_calls(base64.b64decode('Zm9vYmFy'))
        
    @patch('httpx.AsyncClient')
    async def test_generate_image_custom_size(self, mock_httpx):
        """Test image generation with custom size."""
        # Mock successful responses
        self.mock_openai_instance.images.generate.return_value = MagicMock(
            data=[MagicMock(b64_json='Zm9vYmFy')]
        )
        
        # Test with custom size
        await self.image_generator.generate_image('test prompt', size="512x512")
        
        # Verify calls
        self._verify_openai_call('test prompt', size="512x512")
        self._verify_imgur_calls(base64.b64decode('Zm9vYmFy'))
        
    @patch('httpx.AsyncClient')
    async def test_generate_image_failure(self, mock_httpx):
        """Test image generation failure."""
        # Mock OpenAI error
        self.mock_openai_instance.images.generate.side_effect = Exception("API Error")
        
        # Test error handling
        with self.assertRaises(Exception):
            await self.image_generator.generate_image('test prompt')