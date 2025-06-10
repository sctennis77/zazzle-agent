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
@pytest.mark.parametrize("model,default_size,expected_prompt_base,custom_size", [
    ("dall-e-2", "256x256", IMAGE_GENERATION_BASE_PROMPTS["dall-e-2"], "512x512"),
    ("dall-e-3", "1024x1024", IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"], "1024x1792"),
])
@patch('httpx.AsyncClient')
async def test_generate_image_success(mock_httpx, model, default_size, expected_prompt_base, custom_size):
    image_generator = ImageGenerator(model=model)
    mock_openai_instance = MagicMock()
    image_generator.client = mock_openai_instance
    mock_imgur_save = patch('app.clients.imgur_client.ImgurClient.save_image_locally', return_value="test.png").start()
    mock_imgur_upload = patch('app.clients.imgur_client.ImgurClient.upload_image', return_value=("https://i.imgur.com/test.png", "test.png")).start()
    mock_openai_instance.images.generate.return_value = MagicMock(data=[MagicMock(b64_json='Zm9vYmFy')])
    imgur_url, local_path = await image_generator.generate_image('test prompt')
    expected_prompt = f"{expected_prompt_base} test prompt"
    mock_openai_instance.images.generate.assert_called_once_with(
        model=model,
        prompt=expected_prompt,
        size=default_size,
        n=1,
        response_format="b64_json"
    )
    mock_imgur_save.assert_called_once_with(base64.b64decode('Zm9vYmFy'), ANY, subdirectory="generated_products")
    mock_imgur_upload.assert_called_once_with(ANY)
    patch.stopall()

@pytest.mark.asyncio
@pytest.mark.parametrize("model,default_size,expected_prompt_base,custom_size", [
    ("dall-e-2", "256x256", IMAGE_GENERATION_BASE_PROMPTS["dall-e-2"], "512x512"),
    ("dall-e-3", "1024x1024", IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"], "1024x1792"),
])
@patch('httpx.AsyncClient')
async def test_generate_image_custom_size(mock_httpx, model, default_size, expected_prompt_base, custom_size):
    image_generator = ImageGenerator(model=model)
    mock_openai_instance = MagicMock()
    image_generator.client = mock_openai_instance
    mock_imgur_save = patch('app.clients.imgur_client.ImgurClient.save_image_locally', return_value="test.png").start()
    mock_imgur_upload = patch('app.clients.imgur_client.ImgurClient.upload_image', return_value=("https://i.imgur.com/test.png", "test.png")).start()
    mock_openai_instance.images.generate.return_value = MagicMock(data=[MagicMock(b64_json='Zm9vYmFy')])
    await image_generator.generate_image('test prompt', size=custom_size)
    expected_prompt = f"{expected_prompt_base} test prompt"
    mock_openai_instance.images.generate.assert_called_once_with(
        model=model,
        prompt=expected_prompt,
        size=custom_size,
        n=1,
        response_format="b64_json"
    )
    mock_imgur_save.assert_called_once_with(base64.b64decode('Zm9vYmFy'), ANY, subdirectory="generated_products")
    mock_imgur_upload.assert_called_once_with(ANY)
    patch.stopall()

@pytest.mark.asyncio
@pytest.mark.parametrize("model,default_size,expected_prompt_base,custom_size", [
    ("dall-e-2", "256x256", IMAGE_GENERATION_BASE_PROMPTS["dall-e-2"], "512x512"),
    ("dall-e-3", "1024x1024", IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"], "1024x1792"),
])
@patch('httpx.AsyncClient')
async def test_generate_image_failure(mock_httpx, model, default_size, expected_prompt_base, custom_size):
    image_generator = ImageGenerator(model=model)
    mock_openai_instance = MagicMock()
    image_generator.client = mock_openai_instance
    mock_imgur_save = patch('app.clients.imgur_client.ImgurClient.save_image_locally', return_value="test.png").start()
    mock_imgur_upload = patch('app.clients.imgur_client.ImgurClient.upload_image', return_value=("https://i.imgur.com/test.png", "test.png")).start()
    mock_openai_instance.images.generate.side_effect = Exception("API Error")
    with pytest.raises(Exception):
        await image_generator.generate_image('test prompt')
    patch.stopall()