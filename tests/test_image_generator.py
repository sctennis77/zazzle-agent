import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import pytest
import base64
from typing import Tuple, Generator

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
        
        from app.image_generator import ImageGenerator
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
                from app.image_generator import ImageGenerator
                ImageGenerator()

@pytest.mark.asyncio
class TestImageGeneratorAsync:
    @pytest.fixture(autouse=True)
    def setup(self, mock_imgur_responses: Tuple[str, str]) -> Generator[None, None, None]:
        """Setup async test fixtures."""
        # Setup OpenAI mock
        patcher_openai = patch('app.image_generator.OpenAI')
        self.mock_openai = patcher_openai.start()
        self.mock_openai_instance = MagicMock()
        self.mock_openai.return_value = self.mock_openai_instance

        # Setup Imgur mocks
        patcher_imgur_upload = patch('app.clients.imgur_client.ImgurClient.upload_image', 
                                   return_value=mock_imgur_responses)
        self.mock_imgur_upload = patcher_imgur_upload.start()
        
        patcher_imgur_save = patch('app.clients.imgur_client.ImgurClient.save_image_locally', 
                                 return_value=mock_imgur_responses[1])
        self.mock_imgur_save = patcher_imgur_save.start()

        # Import and setup ImageGenerator
        from app.image_generator import ImageGenerator
        self.image_generator = ImageGenerator()
        
        yield
        
        # Cleanup
        patch.stopall()

    def _verify_openai_call(self, prompt: str, size: str = "256x256") -> None:
        """Helper method to verify OpenAI API call."""
        self.mock_openai_instance.images.generate.assert_called_once_with(
            model="dall-e-2",
            prompt=prompt,
            size=size,
            n=1,
            response_format="b64_json"
        )

    def _verify_imgur_calls(self, image_data: bytes) -> None:
        """Helper method to verify Imgur client calls."""
        from app.clients.imgur_client import ImgurClient
        ImgurClient.save_image_locally.assert_called_once_with(
            image_data,
            unittest.mock.ANY,
            subdirectory='generated_products'
        )
        ImgurClient.upload_image.assert_called_once_with('outputs/images/test.png')

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

        # Verify return values
        assert imgur_url == 'https://imgur.com/test.jpg'
        assert local_path == 'outputs/images/test.png'

    @patch('httpx.AsyncClient')
    async def test_generate_image_failure(self, mock_httpx):
        """Test image generation failure."""
        # Mock OpenAI response with no data
        self.mock_openai_instance.images.generate.return_value = MagicMock(
            data=[]
        )

        # Test image generation
        with pytest.raises(Exception):
            await self.image_generator.generate_image('test prompt')

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