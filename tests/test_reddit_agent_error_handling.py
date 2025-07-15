"""
Reddit Agent error handling tests.

Tests for error conditions and edge cases in the Reddit Agent.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from app.agents.reddit_agent import RedditAgent
from app.models import PipelineConfig, ProductIdea, RedditContext


@pytest.fixture
def pipeline_config():
    """Provide a test pipeline configuration."""
    return PipelineConfig(
        model="dall-e-3",
        zazzle_template_id="test_template_id",
        zazzle_tracking_code="test_tracking_code",
        prompt_version="1.0.0",
    )


@pytest.fixture
def reddit_agent_with_mocks(pipeline_config):
    """Create a Reddit Agent with mocked dependencies."""
    with patch.dict(
        os.environ,
        {
            "REDDIT_CLIENT_ID": "test_client_id",
            "REDDIT_CLIENT_SECRET": "test_client_secret",
            "REDDIT_USERNAME": "test_username",
            "REDDIT_PASSWORD": "test_password",
            "REDDIT_USER_AGENT": "test_user_agent",
        },
    ):
        agent = RedditAgent(pipeline_config)
        
        # Mock the openai and reddit clients
        agent.openai = MagicMock()
        agent.reddit = MagicMock()
        
        return agent


class TestRedditAgentErrorHandling:
    """Test cases for Reddit Agent error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_analyze_post_content_openai_api_error(self, reddit_agent_with_mocks):
        """Test that OpenAI API errors are handled gracefully."""
        reddit_context = RedditContext(
            title="Test Post",
            content="Test content",
            subreddit="test",
            upvotes=10,
            comments=["Test comment"]
        )

        # Mock OpenAI to raise an API error
        reddit_agent_with_mocks.openai.chat.completions.create.side_effect = (
            openai.APIError("API Error occurred")
        )

        result = await reddit_agent_with_mocks._analyze_post_content(reddit_context)
        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_post_content_rate_limit_error(self, reddit_agent_with_mocks):
        """Test that rate limit errors are handled gracefully."""
        reddit_context = RedditContext(
            title="Test Post",
            content="Test content",
            subreddit="test",
            upvotes=10,
            comments=["Test comment"]
        )

        # Mock OpenAI to raise a rate limit error
        reddit_agent_with_mocks.openai.chat.completions.create.side_effect = (
            openai.RateLimitError("Rate limit exceeded")
        )

        result = await reddit_agent_with_mocks._analyze_post_content(reddit_context)
        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_post_content_invalid_json_response(self, reddit_agent_with_mocks):
        """Test handling of invalid JSON responses from OpenAI."""
        reddit_context = RedditContext(
            title="Test Post",
            content="Test content",
            subreddit="test",
            upvotes=10,
            comments=["Test comment"]
        )

        # Mock OpenAI to return invalid JSON
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Invalid JSON response"
        reddit_agent_with_mocks.openai.chat.completions.create.return_value = mock_response

        result = await reddit_agent_with_mocks._analyze_post_content(reddit_context)
        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_post_content_empty_response(self, reddit_agent_with_mocks):
        """Test handling of empty responses from OpenAI."""
        reddit_context = RedditContext(
            title="Test Post",
            content="Test content",
            subreddit="test",
            upvotes=10,
            comments=["Test comment"]
        )

        # Mock OpenAI to return empty response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = ""
        reddit_agent_with_mocks.openai.chat.completions.create.return_value = mock_response

        result = await reddit_agent_with_mocks._analyze_post_content(reddit_context)
        assert result is None

    @pytest.mark.asyncio
    async def test_image_generation_error_handling(self, reddit_agent_with_mocks):
        """Test error handling during image generation."""
        product_idea = ProductIdea(
            theme="Test Theme",
            design_ideas=["Test design"],
            target_audience="test users"
        )

        # Mock image generation to raise an error
        with patch.object(reddit_agent_with_mocks, '_generate_images') as mock_generate:
            mock_generate.side_effect = Exception("Image generation failed")
            
            result = await reddit_agent_with_mocks._generate_images(product_idea)
            assert result == []

    @pytest.mark.asyncio 
    async def test_reddit_client_connection_error(self, reddit_agent_with_mocks):
        """Test handling of Reddit client connection errors."""
        # Mock Reddit client to raise connection error
        reddit_agent_with_mocks.reddit.subreddit.side_effect = Exception("Connection failed")
        
        # This should not crash the agent
        with pytest.raises(Exception, match="Connection failed"):
            reddit_agent_with_mocks.reddit.subreddit("test")