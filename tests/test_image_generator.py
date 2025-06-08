import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import pytest
import base64

# Module-level fixture to patch openai.OpenAI for all async tests
@pytest.fixture(autouse=True, scope="module")
def patch_openai():
    with patch('openai.OpenAI') as mock_openai:
        mock_openai_instance = MagicMock()
        mock_openai.return_value = mock_openai_instance
        yield mock_openai, mock_openai_instance

class TestImageGenerator(unittest.TestCase):
    """Test cases for the ImageGenerator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.patcher_env = patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'})
        self.patcher_env.start()
        self.addCleanup(self.patcher_env.stop)
        
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
    def setup(self):
        patcher_openai = patch('app.image_generator.OpenAI')
        self.mock_openai = patcher_openai.start()
        self.mock_openai_instance = MagicMock()
        self.mock_openai.return_value = self.mock_openai_instance
        self.patcher_env = patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'})
        self.patcher_env.start()
        # Patch ImgurClient.upload_image and save_image_locally directly BEFORE importing ImageGenerator
        patcher_imgur_upload = patch('app.clients.imgur_client.ImgurClient.upload_image', return_value=('https://imgur.com/test.jpg', 'outputs/images/test.png'))
        self.mock_imgur_upload = patcher_imgur_upload.start()
        patcher_imgur_save = patch('app.clients.imgur_client.ImgurClient.save_image_locally', return_value='outputs/images/test.png')
        self.mock_imgur_save = patcher_imgur_save.start()
        # Import ImageGenerator only after patching
        from app.image_generator import ImageGenerator
        self.image_generator = ImageGenerator()
        yield
        patch.stopall()
        self.patcher_env.stop()
        patcher_openai.stop()
        patcher_imgur_upload.stop()
        patcher_imgur_save.stop()

    @patch('httpx.AsyncClient')
    async def test_generate_image_success(self, mock_httpx):
        """Test successful image generation and storage."""
        # Mock OpenAI response
        self.mock_openai_instance.images.generate.return_value = MagicMock(
            data=[MagicMock(b64_json='Zm9vYmFy')]
        )

        # Mock httpx response
        mock_httpx_instance = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_httpx_instance
        mock_httpx_instance.get.return_value = MagicMock(
            content=b'test_image_data'
        )

        # Test image generation
        imgur_url, local_path = await self.image_generator.generate_image('test prompt')

        # Verify OpenAI call
        self.mock_openai_instance.images.generate.assert_called_once_with(
            model="dall-e-2",
            prompt='test prompt',
            size="256x256",
            n=1,
            response_format="b64_json"
        )

        # Verify httpx call - This should no longer be called as we are using b64_json
        mock_httpx_instance.get.assert_not_called()

        # Verify local save
        from app.clients.imgur_client import ImgurClient
        ImgurClient.save_image_locally.assert_called_once_with(
            base64.b64decode('Zm9vYmFy'),
            unittest.mock.ANY,
            subdirectory='generated_products'
        )

        # Verify Imgur upload
        from app.clients.imgur_client import ImgurClient
        ImgurClient.upload_image.assert_called_once_with('outputs/images/test.png')

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

        mock_httpx_instance = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_httpx_instance
        mock_httpx_instance.get.return_value = MagicMock(
            content=b'test_image_data'
        )

        # Test with custom size
        await self.image_generator.generate_image('test prompt', size="512x512")

        # Verify size parameter
        self.mock_openai_instance.images.generate.assert_called_once_with(
            model="dall-e-2",
            prompt='test prompt',
            size="512x512",
            n=1,
            response_format="b64_json"
        )

        # Verify httpx call - This should no longer be called as we are using b64_json
        mock_httpx_instance.get.assert_not_called()

        # Verify local save
        from app.clients.imgur_client import ImgurClient
        ImgurClient.save_image_locally.assert_called_once_with(
            base64.b64decode('Zm9vYmFy'),
            unittest.mock.ANY,
            subdirectory='generated_products'
        )

        # Verify Imgur upload
        from app.clients.imgur_client import ImgurClient
        ImgurClient.upload_image.assert_called_once_with('outputs/images/test.png')