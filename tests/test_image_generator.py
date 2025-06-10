import unittest
from unittest.mock import patch, MagicMock, AsyncMock, ANY
import os
import pytest
import base64
from typing import Tuple, Generator
from unittest import IsolatedAsyncioTestCase
from app.image_generator import ImageGenerator, IMAGE_GENERATION_BASE_PROMPTS
from app.models import ProductIdea, RedditContext, ProductInfo, DesignInstructions
import json

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

@pytest.fixture
def image_generator():
    """Create an ImageGenerator instance for testing."""
    return ImageGenerator()

@pytest.fixture
def sample_product_idea():
    """Create a sample product idea for testing."""
    reddit_context = RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit'
    )
    
    return ProductIdea(
        theme='test_theme',
        image_description='Test image description',
        design_instructions={'image': 'https://example.com/image.jpg'},
        reddit_context=reddit_context,
        model='dall-e-3',
        prompt_version='1.0.0'
    )

class TestImageGenerator(IsolatedAsyncioTestCase):
    """Test cases for the ImageGenerator class."""
    
    async def asyncSetUp(self):
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

    async def asyncTearDown(self):
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

    def test_get_prompt_info(self):
        """Test getting prompt info for different models."""
        # Test DALL-E 2
        image_generator = ImageGenerator(model="dall-e-2")
        prompt_info = image_generator.get_prompt_info()
        assert prompt_info["version"] == "1.0.0"
        assert "You are a incredibly talented designer" in prompt_info["prompt"]
        
        # Test DALL-E 3
        image_generator = ImageGenerator(model="dall-e-3")
        prompt_info = image_generator.get_prompt_info()
        assert prompt_info["version"] == "1.0.0"
        assert "You are a incredibly talented designer" in prompt_info["prompt"]

    async def test_generate_image(self):
        """Test generating an image for a product idea."""
        # Mock the image generation
        mock_openai_instance = MagicMock()
        self.image_generator.client = mock_openai_instance
        mock_openai_instance.images.generate.return_value = MagicMock(data=[MagicMock(b64_json='Zm9vYmFy')])
        self.image_generator.imgur_client.save_image_locally = MagicMock(return_value="test.png")
        self.image_generator.imgur_client.upload_image = MagicMock(return_value=("https://i.imgur.com/test.png", "test.png"))
        # Mock _process_and_store_image to return a ProductInfo
        reddit_context = RedditContext(
            post_id='test_post_id',
            post_title='Test Post Title',
            post_url='https://reddit.com/test',
            subreddit='test_subreddit'
        )
        product_idea = ProductIdea(
            theme='test_theme',
            image_description='Test image description',
            design_instructions={'image': 'https://example.com/image.jpg'},
            reddit_context=reddit_context,
            model='dall-e-3',
            prompt_version='1.0.0'
        )
        expected_product_info = ProductInfo(
            product_id='test_id',
            name='Test Product',
            product_type='sticker',
            zazzle_template_id='template123',
            zazzle_tracking_code='tracking456',
            image_url='https://i.imgur.com/test.png',
            product_url='https://example.com/product',
            theme=product_idea.theme,
            model=product_idea.model,
            prompt_version=product_idea.prompt_version,
            reddit_context=product_idea.reddit_context,
            design_instructions=product_idea.design_instructions,
            image_local_path='test.png'
        )
        self.image_generator._process_and_store_image = AsyncMock(return_value=expected_product_info)
        # Generate image
        result = await self.image_generator.generate_image(product_idea)
        # Verify result
        assert isinstance(result, ProductInfo)
        assert result.theme == product_idea.theme
        assert result.model == product_idea.model
        assert result.prompt_version == product_idea.prompt_version
        assert result.reddit_context == product_idea.reddit_context

    async def test_generate_image_error(self):
        """Test error handling in generate_image."""
        # Mock the image generation to raise an exception
        async def mock_generate_image(prompt, model):
            raise Exception("Test error")
        self.image_generator._generate_image = mock_generate_image
        
        # Create a sample product idea
        reddit_context = RedditContext(
            post_id='test_post_id',
            post_title='Test Post Title',
            post_url='https://reddit.com/test',
            subreddit='test_subreddit'
        )
        product_idea = ProductIdea(
            theme='test_theme',
            image_description='Test image description',
            design_instructions={'image': 'https://example.com/image.jpg'},
            reddit_context=reddit_context,
            model='dall-e-3',
            prompt_version='1.0.0'
        )
        
        # Verify that the error is caught and logged
        with pytest.raises(Exception):
            await self.image_generator.generate_image(product_idea)

    async def test_generate_images_batch(self):
        """Test generating images for a batch of product ideas."""
        # Create sample product ideas
        reddit_context = RedditContext(
            post_id='test_post_id',
            post_title='Test Post Title',
            post_url='https://reddit.com/test',
            subreddit='test_subreddit'
        )
        product_ideas = [
            ProductIdea(
                theme='theme1',
                image_description='Description 1',
                design_instructions={'image': 'https://example.com/image1.jpg'},
                reddit_context=reddit_context,
                model='dall-e-3',
                prompt_version='1.0.0'
            ),
            ProductIdea(
                theme='theme2',
                image_description='Description 2',
                design_instructions={'image': 'https://example.com/image2.jpg'},
                reddit_context=reddit_context,
                model='dall-e-3',
                prompt_version='1.0.0'
            )
        ]
        # Mock the image generation
        async def mock_generate_image(prompt, model):
            return {
                'url': f'https://example.com/generated_image_{prompt}.jpg',
                'local_path': f'/path/to/generated_image_{prompt}.jpg'
            }
        self.image_generator._generate_image = mock_generate_image
        # Generate images
        results = await self.image_generator.generate_images_batch(product_ideas)
        # Verify results
        assert len(results) == 2
        assert all(isinstance(result, ProductInfo) for result in results)
        assert results[0].theme == 'theme1'
        assert results[1].theme == 'theme2'

    async def test_generate_images_batch_empty(self):
        """Test generating images for an empty batch."""
        results = await self.image_generator.generate_images_batch([])
        assert len(results) == 0

# Parameterized async tests for image generation (standalone, not in class)
import pytest

@pytest.mark.asyncio
@pytest.mark.parametrize("model,default_size,expected_prompt_base,custom_size", [
    ("dall-e-2", "256x256", IMAGE_GENERATION_BASE_PROMPTS["dall-e-2"]["prompt"], "512x512"),
    ("dall-e-3", "1024x1024", IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["prompt"], "1024x1792"),
])
async def test_generate_image_success(model, default_size, expected_prompt_base, custom_size):
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
    ("dall-e-2", "256x256", IMAGE_GENERATION_BASE_PROMPTS["dall-e-2"]["prompt"], "512x512"),
    ("dall-e-3", "1024x1024", IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]["prompt"], "1024x1792"),
])
async def test_generate_image_custom_size(model, default_size, expected_prompt_base, custom_size):
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
async def test_generate_image_failure(model, default_size, expected_prompt_base, custom_size):
    image_generator = ImageGenerator(model=model)
    mock_openai_instance = MagicMock()
    image_generator.client = mock_openai_instance
    mock_imgur_save = patch('app.clients.imgur_client.ImgurClient.save_image_locally', return_value="test.png").start()
    mock_imgur_upload = patch('app.clients.imgur_client.ImgurClient.upload_image', return_value=("https://i.imgur.com/test.png", "test.png")).start()
    mock_openai_instance.images.generate.side_effect = Exception("API Error")
    with pytest.raises(Exception):
        await image_generator.generate_image('test prompt')
    patch.stopall()