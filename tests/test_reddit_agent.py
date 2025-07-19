"""
Reddit Agent tests - simplified and focused on core functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.reddit_agent import RedditAgent, pick_subreddit
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
def reddit_agent(pipeline_config):
    """Create a Reddit Agent with mocked dependencies."""
    mock_reddit_client = MagicMock()
    mock_openai_client = MagicMock()

    with patch(
        "app.agents.reddit_agent.openai.OpenAI", return_value=mock_openai_client
    ):
        with patch(
            "app.agents.reddit_agent.praw.Reddit", return_value=mock_reddit_client
        ):
            agent = RedditAgent(config=pipeline_config)
            # Directly assign mocks to ensure they're used
            agent.openai = mock_openai_client
            agent.reddit_client = mock_reddit_client
            agent.session = None  # Avoid database checks
            return agent


class TestRedditAgent:
    """Test cases for the Reddit Agent."""

    def test_pick_subreddit_returns_string(self, db_session):
        """Test that pick_subreddit returns a valid subreddit string."""
        result = pick_subreddit(db_session)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_determine_product_idea_success(self, reddit_agent):
        """Test successful product idea determination."""
        reddit_context = RedditContext(
            post_id="test123",
            post_title="Funny Cat Meme",
            post_url="https://reddit.com/r/cats/test123",
            post_content="This is a funny meme about cats",
            subreddit="cats",
            score=100,
            comments=[{"text": "Great meme!"}],
        )

        # Mock OpenAI response in correct format
        reddit_agent.openai.chat.completions.create.return_value.choices[
            0
        ].message.content = "Theme: Cat Humor\nImage Title: Funny Cat Meme\nImage Description: A funny cat doing something cute"

        result = await reddit_agent._determine_product_idea(reddit_context)

        assert result is not None
        assert result.theme == "Cat Humor"
        assert result.image_description == "A funny cat doing something cute"
        assert result.design_instructions.get("image_title") == "Funny Cat Meme"

    @pytest.mark.asyncio
    async def test_determine_product_idea_markdown_bold_format(self, reddit_agent):
        """Test product idea determination with markdown bold format response."""
        reddit_context = RedditContext(
            post_id="test123",
            post_title="Card Collection Post",
            post_url="https://reddit.com/r/cards/test123",
            post_content="Discussion about card packs vs singles",
            subreddit="cards",
            score=100,
            comments=[
                {"text": "Packs are more exciting but singles are more efficient"}
            ],
        )

        # Mock OpenAI response with markdown bold format (like newer models use)
        reddit_agent.openai.chat.completions.create.return_value.choices[
            0
        ].message.content = '**Theme:** The tension between chaos and control in card collecting\n**Image Title:** "Chance vs. Choice: The Duel of Decks"\n**Image Description:** A vibrant card shop with swirling packs on left and organized singles on right'

        result = await reddit_agent._determine_product_idea(reddit_context)

        assert result is not None
        assert (
            result.theme == "The tension between chaos and control in card collecting"
        )
        assert (
            result.image_description
            == "A vibrant card shop with swirling packs on left and organized singles on right"
        )
        assert (
            result.design_instructions.get("image_title")
            == "Chance vs. Choice: The Duel of Decks"
        )

    @pytest.mark.asyncio
    async def test_determine_product_idea_handles_errors(self, reddit_agent):
        """Test that _determine_product_idea handles errors gracefully."""
        reddit_context = RedditContext(
            post_id="test123",
            post_title="Test Post",
            post_url="https://reddit.com/test",
            post_content="Test content",
            subreddit="test",
            score=100,
            comments=[{"text": "Test comment"}],
        )

        # Mock OpenAI to raise an exception
        reddit_agent.openai.chat.completions.create.side_effect = Exception("API Error")

        result = await reddit_agent._determine_product_idea(reddit_context)
        assert result is None

    @pytest.mark.asyncio
    async def test_find_and_create_product_no_posts(self, reddit_agent):
        """Test handling when no suitable posts are found."""
        # Mock empty results from Reddit
        reddit_agent.reddit_client.reddit.subreddit().hot.return_value = []

        result = await reddit_agent.find_and_create_product_for_task()
        assert result is None

    @pytest.mark.asyncio
    async def test_find_and_create_product_success(self, reddit_agent):
        """Test successful product creation from Reddit post."""
        # Create a comprehensive mock submission
        mock_submission = MagicMock()
        mock_submission.id = "test_post_123"
        mock_submission.title = "Amazing Test Post"
        mock_submission.selftext = "This is test content"
        mock_submission.score = 100
        mock_submission.num_comments = 50
        mock_submission.author.name = "test_author"
        mock_submission.subreddit.display_name = "test"
        mock_submission.url = "https://reddit.com/test"
        mock_submission.permalink = "/r/test/test"
        mock_submission.stickied = False
        mock_submission.created_utc = 1752579513
        mock_submission.is_self = True

        # Mock comments
        mock_comment = MagicMock()
        mock_comment.body = "Great post!"
        mock_submission.comments.replace_more = MagicMock()
        mock_submission.comments.list.return_value = [mock_comment]

        reddit_agent.reddit_client.reddit.subreddit().hot.return_value = [
            mock_submission
        ]

        # Mock OpenAI responses for both comment summary and product idea
        openai_responses = [
            MagicMock(),  # First call: comment summary
            MagicMock(),  # Second call: product idea
        ]
        openai_responses[0].choices[0].message.content = "Test comment summary"
        openai_responses[1].choices[
            0
        ].message.content = "Theme: Test Theme\nImage Title: Amazing Test Title\nImage Description: A vivid and creative test image"
        reddit_agent.openai.chat.completions.create.side_effect = openai_responses

        # Mock image generation and product creation
        with patch("app.agents.reddit_agent.AsyncImageGenerator") as mock_image_gen:
            with patch(
                "app.agents.reddit_agent.ZazzleProductDesigner"
            ) as mock_designer:
                mock_image_gen.return_value.generate_image = AsyncMock()
                mock_image_gen.return_value.generate_image.return_value = (
                    "https://example.com/image.jpg",
                    "/tmp/test.jpg",
                )

                # Mock product creation to return a realistic product
                mock_designer.return_value.create_product = AsyncMock()
                mock_designer.return_value.create_product.return_value = MagicMock(
                    theme="Test Theme",
                    product_url="https://www.zazzle.com/test-product",
                )

                result = await reddit_agent.find_and_create_product_for_task()

                assert result is not None
                assert result.theme == "Test Theme"
                assert "zazzle.com" in result.product_url
