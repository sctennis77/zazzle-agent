import pytest
import json
import os
from unittest.mock import patch, MagicMock
from openai import APIError
from app.content_generator import ContentGenerator, generate_content_from_config
from app.models import ProductInfo

@pytest.fixture
def content_generator():
    return ContentGenerator()

@pytest.fixture
def mock_product():
    return ProductInfo(
        product_id="test123",
        name="Test Product",
        product_type="sticker",
        image_url="https://example.com/image.jpg",
        product_url="https://example.com/product",
        zazzle_template_id="123",
        zazzle_tracking_code="TEST",
        theme="Test Theme",
        model="test-model",
        prompt_version="1.0",
        design_instructions={}
    )

def test_generate_content_invalid_json(content_generator):
    """Test handling of invalid JSON response from API."""
    with patch('openai.OpenAI') as mock_openai:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is not JSON"
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        content = content_generator.generate_content("Test Product")
        assert content == "Error generating content"

def test_generate_content_malformed_json(content_generator):
    """Test handling of malformed JSON response from API."""
    with patch('openai.OpenAI') as mock_openai:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value", "unclosed": }'
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        content = content_generator.generate_content("Test Product")
        assert content == "Error generating content"

def test_generate_content_api_rate_limit(content_generator):
    """Test handling of API rate limiting."""
    with patch('openai.OpenAI') as mock_openai:
        mock_openai.return_value.chat.completions.create.side_effect = APIError(
            message="Rate limit exceeded",
            request=MagicMock(),
            body=None
        )
        
        content = content_generator.generate_content("Test Product")
        assert content == "Error generating content"

def test_generate_content_network_error(content_generator):
    """Test handling of network errors."""
    with patch('openai.OpenAI') as mock_openai:
        mock_openai.return_value.chat.completions.create.side_effect = Exception("Network error")
        
        content = content_generator.generate_content("Test Product")
        assert content == "Error generating content"

def test_generate_content_empty_product_name(content_generator):
    """Test handling of empty product names."""
    content = content_generator.generate_content("")
    assert content == "Error generating content"

def test_generate_content_special_characters(content_generator):
    """Test handling of product names with special characters."""
    with patch('openai.OpenAI') as mock_openai:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        content = content_generator.generate_content("Product!@#$%^&*()")
        assert isinstance(content, str)
        assert len(content) > 0

@patch('os.getenv')
def test_generate_content_from_config_missing_api_key(mock_getenv):
    """Test handling of missing API key."""
    mock_getenv.return_value = None
    result = generate_content_from_config()
    assert result is None

@patch('builtins.open')
@patch('os.getenv')
def test_generate_content_from_config_missing_file(mock_getenv, mock_open):
    """Test handling of missing configuration file."""
    mock_getenv.return_value = "test_api_key"
    mock_open.side_effect = FileNotFoundError()
    result = generate_content_from_config()
    assert result is None

@patch('builtins.open')
@patch('os.getenv')
def test_generate_content_from_config_invalid_json(mock_getenv, mock_open):
    """Test handling of invalid JSON in configuration file."""
    mock_getenv.return_value = "test_api_key"
    mock_open.return_value.__enter__.return_value.read.return_value = "invalid json"
    result = generate_content_from_config()
    assert result is None

@patch('builtins.open')
@patch('os.getenv')
def test_generate_content_from_config_empty_products(mock_getenv, mock_open):
    """Test handling of empty products list in configuration file."""
    mock_getenv.return_value = "test_api_key"
    mock_open.return_value.__enter__.return_value.read.return_value = "[]"
    result = generate_content_from_config()
    assert result == {} 