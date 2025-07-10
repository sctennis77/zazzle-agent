import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from app.agents.reddit_agent import RedditAgent
from app.models import PipelineConfig, ProductIdea, RedditContext
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class TestRedditAgentErrorHandling(unittest.IsolatedAsyncioTestCase):
    """Test cases for Reddit Agent error handling and edge cases."""

    async def asyncSetUp(self):
        """Set up the test environment."""
        self.config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id="test_template_id",
            zazzle_tracking_code="test_tracking_code",
            prompt_version="1.0.0",
        )
        
        # Create the RedditAgent first
        self.reddit_agent = RedditAgent(self.config)
        
        # Mock the openai attribute of the RedditAgent instance
        self.mock_openai_instance = MagicMock()
        self.reddit_agent.openai = self.mock_openai_instance
        
        # Mock the reddit client
        self.reddit_agent.reddit = MagicMock()

        # Mock environment variables
        self.patcher_env = patch.dict(
            os.environ,
            {
                "REDDIT_CLIENT_ID": "test_client_id",
                "REDDIT_CLIENT_SECRET": "test_client_secret",
                "REDDIT_USERNAME": "test_username",
                "REDDIT_PASSWORD": "test_password",
                "REDDIT_USER_AGENT": "test_user_agent",
            },
        )
        self.patcher_env.start()
        self.addCleanup(self.patcher_env.stop)

    async def test_determine_product_idea_empty_response(self):
        """Test handling of empty OpenAI response."""
        # Mock empty response
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=""))]
        )

        reddit_context = RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        )

        result = await self.reddit_agent._determine_product_idea(reddit_context)
        self.assertIsNone(result)

    async def test_determine_product_idea_missing_theme(self):
        """Test handling of response missing theme."""
        # Mock response with only image description
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content="Image Description: A beautiful sunset")
                )
            ]
        )

        reddit_context = RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        )

        result = await self.reddit_agent._determine_product_idea(reddit_context)
        self.assertIsNone(result)

    async def test_determine_product_idea_missing_image_description(self):
        """Test handling of response missing image description."""
        # Mock response with only theme
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Theme: Beautiful Sunset"))]
        )

        reddit_context = RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        )

        with self.assertRaises(ValueError):
            await self.reddit_agent._determine_product_idea(reddit_context)

    async def test_determine_product_idea_openai_error(self):
        """Test handling of OpenAI API error."""
        # Mock OpenAI API error
        mock_error = openai.APIError("API Error", request=MagicMock(), body={})
        self.mock_openai_instance.chat.completions.create.side_effect = mock_error

        reddit_context = RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        )

        result = await self.reddit_agent._determine_product_idea(reddit_context)
        self.assertIsNone(result)

    @patch("app.image_generator.ImageGenerator.generate_image", new_callable=AsyncMock)
    async def test_find_and_create_product_for_task_image_generation_failure(
        self, mock_generate_image
    ):
        """Test handling of image generation failure."""
        # Mock successful product idea generation
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="Theme: Test Theme\nImage Description: Test image"
                    )
                )
            ]
        )

        # Mock image generation failure
        mock_generate_image.side_effect = Exception("Image generation failed")

        result = await self.reddit_agent.find_and_create_product_for_task()
        self.assertIsNone(result)

    @patch(
        "app.zazzle_product_designer.ZazzleProductDesigner.create_product",
        new_callable=AsyncMock,
    )
    async def test_find_and_create_product_for_task_creation_failure(self, mock_create_product):
        """Test handling of product creation failure."""
        # Mock successful product idea generation
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="Theme: Test Theme\nImage Description: Test image"
                    )
                )
            ]
        )

        # Mock successful image generation
        with patch(
            "app.image_generator.ImageGenerator.generate_image", new_callable=AsyncMock
        ) as mock_generate_image:
            mock_generate_image.return_value = (
                "https://example.com/image.jpg",
                "/tmp/image.jpg",
            )

            # Mock product creation failure
            mock_create_product.return_value = None

            result = await self.reddit_agent.find_and_create_product_for_task()
            self.assertIsNone(result)

    async def test_save_reddit_context_to_db_error(self):
        """Test handling of database persistence error."""
        # Mock session that raises an error
        mock_session = MagicMock()
        mock_session.add.side_effect = Exception("Database error")
        self.reddit_agent.session = mock_session
        self.reddit_agent.pipeline_run_id = 1

        reddit_context = RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        )

        # The method should handle the exception and return None
        result = self.reddit_agent.save_reddit_context_to_db(reddit_context)
        self.assertIsNone(result)
        mock_session.add.assert_called_once()

    @patch(
        "app.agents.reddit_agent.RedditAgent._find_trending_post",
        new_callable=AsyncMock,
    )
    async def test_find_and_create_product_for_task_no_trending_post(
        self, mock_find_trending_post
    ):
        """Test handling when no trending post is found."""
        # Mock no trending post found
        mock_find_trending_post.return_value = None

        result = await self.reddit_agent.find_and_create_product_for_task()
        self.assertIsNone(result)

    async def test_determine_product_idea_invalid_theme(self):
        """Test handling of invalid theme in response."""
        # Mock response with invalid theme
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="Theme: default theme\nImage Description: Test image"
                    )
                )
            ]
        )

        reddit_context = RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        )

        with self.assertRaises(ValueError):
            await self.reddit_agent._determine_product_idea(reddit_context)

    async def test_determine_product_idea_empty_image_description(self):
        """Test handling of empty image description in response."""
        # Mock response with empty image description
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content="Theme: Test Theme\nImage Description: ")
                )
            ]
        )

        reddit_context = RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        )

        with self.assertRaises(ValueError):
            await self.reddit_agent._determine_product_idea(reddit_context)
