import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import os
import pytest
from app.image_generator import ImageGenerator

class TestImageGenerator(unittest.TestCase):
    """Test cases for the ImageGenerator class."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_api_key = "test_api_key"
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'OPENAI_API_KEY': self.mock_api_key
        })
        self.env_patcher.start()
        
        # Mock ImgurClient
        self.imgur_patcher = patch('app.image_generator.ImgurClient')
        self.mock_imgur_client = self.imgur_patcher.start()
        self.mock_imgur_instance = MagicMock()
        self.mock_imgur_client.return_value = self.mock_imgur_instance
        
        self.image_generator = ImageGenerator()
        
    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
        self.imgur_patcher.stop()
        
    def test_init_with_api_key(self):
        """Test initialization with valid API key."""
        self.assertEqual(self.image_generator.client.api_key, self.mock_api_key)
        
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                ImageGenerator()

@pytest.mark.asyncio
class TestImageGeneratorAsync:
    """Async test cases for the ImageGenerator class."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.mock_api_key = "test_api_key"
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'OPENAI_API_KEY': self.mock_api_key
        })
        self.env_patcher.start()

        # Patch app.image_generator.OpenAI
        self.openai_patcher = patch('app.image_generator.OpenAI')
        self.mock_openai_client_class = self.openai_patcher.start()
        self.mock_openai_instance = MagicMock()
        self.mock_openai_client_class.return_value = self.mock_openai_instance
        
        # Mock ImgurClient
        self.imgur_patcher = patch('app.image_generator.ImgurClient')
        self.mock_imgur_client = self.imgur_patcher.start()
        self.mock_imgur_instance = MagicMock()
        self.mock_imgur_client.return_value = self.mock_imgur_instance
        
        self.image_generator = ImageGenerator()
        
        yield
        
        # Cleanup
        self.env_patcher.stop()
        self.openai_patcher.stop()
        self.imgur_patcher.stop()
                
    @patch('httpx.AsyncClient')
    async def test_generate_image_success(self, mock_httpx):
        """Test successful image generation and storage."""
        # Mock OpenAI response
        self.mock_openai_instance.images.generate.return_value = MagicMock(
            data=[MagicMock(url='https://dalle.example.com/test.jpg')]
        )
        
        # Mock httpx response
        mock_httpx_instance = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_httpx_instance
        mock_httpx_instance.get.return_value = MagicMock(
            content=b'test_image_data'
        )
        
        # Mock ImgurClient methods
        self.mock_imgur_instance.save_image_locally.return_value = 'outputs/images/test.png'
        self.mock_imgur_instance.upload_image.return_value = ('https://imgur.com/test.jpg', 'outputs/images/test.png')
        
        # Test image generation
        imgur_url, local_path = await self.image_generator.generate_image('test prompt')
        
        # Verify OpenAI call
        self.mock_openai_instance.images.generate.assert_called_once_with(
            model="dall-e-2",
            prompt='test prompt',
            size="256x256",
            n=1
        )
        
        # Verify httpx call
        mock_httpx_instance.get.assert_called_once_with('https://dalle.example.com/test.jpg')
        
        # Verify local save
        self.mock_imgur_instance.save_image_locally.assert_called_once_with(
            b'test_image_data',
            unittest.mock.ANY
        )
        
        # Verify Imgur upload
        self.mock_imgur_instance.upload_image.assert_called_once_with('outputs/images/test.png')
        
        # Verify return values
        assert imgur_url == 'https://imgur.com/test.jpg'
        assert local_path == 'outputs/images/test.png'
        
    async def test_generate_image_failure(self):
        """Test image generation failure."""
        # Mock OpenAI error
        self.mock_openai_instance.images.generate.side_effect = Exception("DALL-E API error")
        
        # Test error handling
        with pytest.raises(Exception):
            await self.image_generator.generate_image('test prompt')
            
    @patch('httpx.AsyncClient')
    async def test_generate_image_custom_size(self, mock_httpx):
        """Test image generation with custom size."""
        # Mock successful responses
        self.mock_openai_instance.images.generate.return_value = MagicMock(
            data=[MagicMock(url='https://dalle.example.com/test.jpg')]
        )
        
        mock_httpx_instance = AsyncMock()
        mock_httpx.return_value.__aenter__.return_value = mock_httpx_instance
        mock_httpx_instance.get.return_value = MagicMock(
            content=b'test_image_data'
        )
        
        self.mock_imgur_instance.save_image_locally.return_value = 'outputs/images/test.png'
        self.mock_imgur_instance.upload_image.return_value = ('https://imgur.com/test.jpg', 'outputs/images/test.png')
        
        # Test with custom size
        await self.image_generator.generate_image('test prompt', size="512x512")
        
        # Verify size parameter
        self.mock_openai_instance.images.generate.assert_called_once_with(
            model="dall-e-2",
            prompt='test prompt',
            size="512x512",
            n=1
        ) 