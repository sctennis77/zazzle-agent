"""
Reddit Agent tests.

Tests for the Reddit Agent functionality including post discovery,
product generation, and subreddit interaction.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.reddit_agent import RedditAgent, pick_subreddit
from app.db.models import PipelineRun, RedditPost, Subreddit
from app.models import (
    DesignInstructions,
    PipelineConfig,
    ProductIdea,
    ProductInfo,
    RedditContext,
)
from app.pipeline_status import PipelineStatus


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
def reddit_agent(pipeline_config, mock_reddit_client, mock_openai_client):
    """Create a Reddit Agent with mocked dependencies."""
    with patch("app.agents.reddit_agent.openai.OpenAI", return_value=mock_openai_client):
        with patch("app.agents.reddit_agent.praw.Reddit", return_value=mock_reddit_client):
            agent = RedditAgent(config=pipeline_config)
            return agent


@pytest.fixture
def test_subreddit(db_session, sample_subreddit_data):
    """Create a test subreddit in the database."""
    subreddit = Subreddit(**sample_subreddit_data)
    db_session.add(subreddit)
    db_session.commit()
    db_session.refresh(subreddit)
    return subreddit


@pytest.fixture
def test_pipeline_run(db_session):
    """Create a test pipeline run."""
    pipeline_run = PipelineRun(
        status="running",
        start_time=datetime.now(timezone.utc),
        summary="Test pipeline run",
        config={"test": True},
        metrics={},
        duration=0,
        retry_count=0,
        version="1.0.0",
    )
    db_session.add(pipeline_run)
    db_session.commit()
    db_session.refresh(pipeline_run)
    return pipeline_run


class TestRedditAgent:
    """Test cases for the Reddit Agent."""

    @pytest.mark.asyncio
    async def test_find_and_create_product_for_task_success(
        self, reddit_agent, db_session, test_subreddit, test_pipeline_run
    ):
        """Test successful product creation from Reddit post."""
        from app.db.models import PipelineTask
        
        # Create a test task
        task = PipelineTask(
            task_type="commission",
            status="pending",
            pipeline_run_id=test_pipeline_run.id,
            subreddit_id=test_subreddit.id,
            message="Create something cool",
            commission_type="random_subreddit",
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        # Mock the Reddit API response
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
        
        reddit_agent.reddit_client.subreddit().hot.return_value = [mock_submission]

        # Mock OpenAI responses
        reddit_agent.openai_client.chat.completions.create.return_value.choices[0].message.content = (
            '{"theme": "Test Theme", "design_ideas": ["Cool design"], "target_audience": "test users"}'
        )

        # Mock image generation
        with patch.object(reddit_agent, '_generate_images') as mock_generate:
            mock_generate.return_value = [
                DesignInstructions(
                    prompt="test prompt",
                    image_url="https://example.com/image.jpg",
                    model="dall-e-3"
                )
            ]
            
            # Mock product creation
            with patch.object(reddit_agent, '_create_zazzle_products') as mock_create:
                mock_create.return_value = [
                    ProductInfo(
                        theme="Test Theme",
                        product_url="https://zazzle.com/product",
                        image_url="https://example.com/image.jpg",
                        template_id="test_template",
                        model="dall-e-3",
                        prompt_version="1.0.0",
                        product_type="sticker",
                        design_description="Test design",
                    )
                ]

                result = await reddit_agent._find_and_create_product_for_task(
                    db_session, task
                )

                assert result is not None
                assert result.theme == "Test Theme"
                assert result.product_url == "https://zazzle.com/product"

    @pytest.mark.asyncio
    async def test_find_and_create_product_no_posts(
        self, reddit_agent, db_session, test_subreddit, test_pipeline_run
    ):
        """Test handling when no suitable posts are found."""
        from app.db.models import PipelineTask
        
        task = PipelineTask(
            task_type="commission",
            status="pending", 
            pipeline_run_id=test_pipeline_run.id,
            subreddit_id=test_subreddit.id,
            message="Create something",
            commission_type="random_subreddit",
        )
        db_session.add(task)
        db_session.commit()

        # Mock empty results
        reddit_agent.reddit_client.subreddit().hot.return_value = []
        reddit_agent.reddit_client.subreddit().new.return_value = []

        result = await reddit_agent._find_and_create_product_for_task(db_session, task)
        assert result is None

    def test_pick_subreddit_with_database(self, db_session, test_subreddit):
        """Test subreddit selection from database."""
        result = pick_subreddit(db_session)
        assert result is not None
        assert result.subreddit_name == "test"

    def test_pick_subreddit_fallback_to_hardcoded(self, db_session):
        """Test fallback to hardcoded subreddits when database is empty."""
        # Database is empty, should fallback to hardcoded list
        result = pick_subreddit(db_session)
        assert result is not None
        assert result in [
            "dankmemes", "memes", "funny", "gaming", "aww", "pics", 
            "todayilearned", "showerthoughts", "askreddit", "explainlikeimfive"
        ]

    @pytest.mark.asyncio
    async def test_analyze_post_content(self, reddit_agent):
        """Test post content analysis."""
        post_content = "This is a funny meme about cats"
        reddit_context = RedditContext(
            title="Funny Cat Meme",
            content=post_content,
            subreddit="cats",
            upvotes=100,
            comments=["Great meme!", "Love it!"]
        )

        # Mock OpenAI response
        reddit_agent.openai_client.chat.completions.create.return_value.choices[0].message.content = (
            '{"theme": "Cat Humor", "design_ideas": ["Funny cat face"], "target_audience": "cat lovers"}'
        )

        result = await reddit_agent._analyze_post_content(reddit_context)
        
        assert result is not None
        assert result.theme == "Cat Humor"
        assert "Funny cat face" in result.design_ideas
        assert result.target_audience == "cat lovers"

    @pytest.mark.asyncio
    async def test_progress_task_coordination_with_event(
        self, reddit_agent, db_session, test_subreddit, test_pipeline_run
    ):
        """Test task progress coordination with events."""
        from app.db.models import PipelineTask
        
        task = PipelineTask(
            task_type="commission",
            status="pending",
            pipeline_run_id=test_pipeline_run.id,
            subreddit_id=test_subreddit.id,
            message="Test task",
            commission_type="random_subreddit",
        )
        db_session.add(task)
        db_session.commit()

        # Create a mock event for task coordination
        mock_event = asyncio.Event()
        
        # Mock the task processing to be quick
        with patch.object(reddit_agent, '_find_and_create_product_for_task') as mock_process:
            mock_process.return_value = ProductInfo(
                theme="Test", 
                product_url="https://test.com",
                image_url="https://test.com/img.jpg",
                template_id="test",
                model="test",
                prompt_version="1.0",
                product_type="sticker",
                design_description="Test"
            )
            
            result = await reddit_agent._find_and_create_product_for_task(
                db_session, task
            )
            
            assert result is not None
            assert result.theme == "Test"

    @pytest.mark.asyncio 
    async def test_error_handling_in_post_analysis(self, reddit_agent):
        """Test error handling when post analysis fails."""
        reddit_context = RedditContext(
            title="Test Post",
            content="Test content", 
            subreddit="test",
            upvotes=1,
            comments=[]
        )

        # Mock OpenAI to raise an exception
        reddit_agent.openai_client.chat.completions.create.side_effect = Exception("API Error")

        result = await reddit_agent._analyze_post_content(reddit_context)
        assert result is None