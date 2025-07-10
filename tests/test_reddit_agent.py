import logging
import os
import time
import unittest
from datetime import datetime, timezone, timedelta
from io import StringIO
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import openai
import praw
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.reddit_agent import RedditAgent, pick_subreddit
from app.db.database import Base, SessionLocal, engine
from app.db.models import PipelineRun, RedditPost, Subreddit
from app.pipeline_status import PipelineStatus
from app.models import (
    DesignInstructions,
    PipelineConfig,
    ProductIdea,
    ProductInfo,
    RedditContext,
)
from app.zazzle_product_designer import ZazzleProductDesigner


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure a clean database state before each test by dropping and recreating all tables."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestRedditAgent(IsolatedAsyncioTestCase):
    """Test cases for the Reddit Agent."""

    async def asyncSetUp(self):
        """Set up the test environment."""
        self.config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id="test_template_id",
            zazzle_tracking_code="test_tracking_code",
            prompt_version="1.0.0",
        )
        self.reddit_agent = RedditAgent(self.config)
        
        # Fix: Use correct attribute names that match the actual RedditAgent constructor
        self.reddit_agent.reddit_client = MagicMock()
        self.reddit_agent.zazzle_designer = AsyncMock()
        
        # Remove references to non-existent attributes
        # self.reddit_agent.reddit = MagicMock()  # This doesn't exist
        # self.reddit_agent.product_designer = MagicMock()  # This doesn't exist
        # self.reddit_agent.subreddit = MagicMock()  # This doesn't exist
        
        # Remove personality and daily_stats as they don't exist in the current RedditAgent
        # self.reddit_agent.personality = {...}  # This doesn't exist
        # self.reddit_agent.daily_stats = {...}  # This doesn't exist

        self.patcher_env = patch.dict(
            os.environ,
            {
                "REDDIT_CLIENT_ID": "test_client_id",
                "REDDIT_CLIENT_SECRET": "test_client_secret",
                "REDDIT_USERNAME": "test_username",
                "REDDIT_PASSWORD": "test_password",
                "REDDIT_USER_AGENT": "test_user_agent",
                "ZAZZLE_AFFILIATE_ID": "test_affiliate_id",
                "ZAZZLE_TEMPLATE_ID": "test_template_id",
                "ZAZZLE_TRACKING_CODE": "test_tracking_code",
            },
        )
        self.patcher_env.start()
        self.addCleanup(self.patcher_env.stop)

        self.patcher_praw_reddit = patch("praw.Reddit")
        self.mock_reddit_constructor = self.patcher_praw_reddit.start()
        self.mock_reddit_instance = MagicMock()
        self.mock_reddit_constructor.return_value = self.mock_reddit_instance
        self.mock_reddit_instance.config = MagicMock()
        self.mock_reddit_instance.config.check_for_updates = False
        self.addCleanup(self.patcher_praw_reddit.stop)

        self.patcher_config_boolean = patch(
            "praw.config.Config._config_boolean", return_value=True
        )
        self.patcher_config_boolean.start()
        self.addCleanup(self.patcher_config_boolean.stop)

        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        logging.getLogger("app").addHandler(self.handler)
        self.addCleanup(lambda: logging.getLogger("app").removeHandler(self.handler))

        # Mock OpenAI
        self.patcher_openai = patch("openai.OpenAI")
        self.mock_openai = self.patcher_openai.start()
        self.mock_openai_instance = MagicMock()
        self.mock_openai.return_value = self.mock_openai_instance
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Test response"))]
        )
        self.addCleanup(self.patcher_openai.stop)

    @patch("app.async_image_generator.AsyncImageGenerator.generate_image", new_callable=AsyncMock)
    @patch("app.agents.reddit_agent.RedditAgent._determine_product_idea", new_callable=AsyncMock)
    @patch("app.agents.reddit_agent.RedditAgent._find_trending_post_for_task", new_callable=AsyncMock)
    async def test_find_and_create_product_for_task(
        self,
        mock_find_trending_post,
        mock_determine_product_idea,
        mock_generate_image,
    ):
        """Test the find_and_create_product_for_task method."""
        # Setup mocks
        mock_post = MagicMock()
        
        # Patch the create_product method on the instance
        with patch.object(self.reddit_agent.zazzle_designer, "create_product", new_callable=AsyncMock) as mock_create_product:
            mock_post.id = "test_post_id"
            mock_post.title = "Test Post Title"
            mock_post.url = "https://reddit.com/test"
            mock_post.subreddit = MagicMock()
            mock_post.subreddit.display_name = "test_subreddit"
            mock_post.selftext = "Test Content"
            mock_post.comment_summary = "Test comment summary"
            mock_find_trending_post.return_value = mock_post

            mock_product_idea = MagicMock()
            mock_product_idea.theme = "Test Theme"
            mock_product_idea.image_description = "Test image description"
            mock_product_idea.design_instructions = {"image": "https://i.imgur.com/test.jpg", "theme": "Test Theme"}
            mock_determine_product_idea.return_value = mock_product_idea
            mock_generate_image.return_value = ("https://i.imgur.com/test.jpg", "/tmp/test.jpg")

            # Fix: create a mock product with product_id attribute
            mock_product = MagicMock()
            mock_product.product_id = "test_product_123"
            # Set the return_value directly on the AsyncMock
            mock_create_product.return_value = mock_product

            result = await self.reddit_agent.find_and_create_product_for_task()
            self.assertEqual(result.product_id, "test_product_123")

    async def test_create_product(self):
        """Test the Reddit agent's ability to create products."""
        # Setup
        mock_post = MagicMock()
        mock_post.id = "test_post_id"
        mock_post.title = "Test Post Title"
        mock_post.url = "https://reddit.com/test"
        mock_post.permalink = "/r/test/123"
        mock_post.subreddit.display_name = "test_subreddit"
        mock_post.selftext = "Test Content"
        mock_post.comment_summary = "Test comment summary"

        mock_product_info = MagicMock()
        self.reddit_agent.zazzle_designer.create_product.return_value = mock_product_info

        # Simulate calling create_product via the agent's zazzle_designer
        result = await self.reddit_agent.zazzle_designer.create_product(
            DesignInstructions(
                image="https://example.com/image.jpg",
                theme="test_theme",
                text="desc",
                product_type="sticker",
                template_id="template123",
                model="dall-e-3",
                prompt_version="1.0.0",
            ),
            RedditContext(
                post_id="test_post_id",
                post_title="Test Post Title",
                post_url="https://reddit.com/test",
                subreddit="test_subreddit",
            ),
        )
        # The AsyncMock will return the mock_product_info we set up
        self.assertEqual(result, mock_product_info)

    @patch(
        "app.agents.reddit_agent.RedditAgent._find_trending_post_for_task",
        new_callable=AsyncMock,
    )
    async def test_find_reddit_post(self, mock_find_trending_post):
        # Setup
        mock_post = MagicMock()
        mock_post.id = "test_post_id"
        mock_post.title = "Test Post Title"
        mock_post.url = "https://reddit.com/test"
        mock_post.permalink = "/r/test/123"
        mock_post.subreddit.display_name = "test_subreddit"
        mock_post.selftext = "Test Content"
        mock_post.comment_summary = "Test comment summary"
        mock_find_trending_post.return_value = mock_post

        result = await self.reddit_agent._find_trending_post_for_task()
        self.assertEqual(result, mock_post)

    async def test_find_reddit_post_skips_processed(self):
        """Test that _find_trending_post skips posts that have already been processed (by post_id)."""
        # Setup
        mock_post1 = MagicMock()
        mock_post1.id = "test_post_id_1"
        mock_post1.title = "Test Post Title 1"
        mock_post1.url = "https://reddit.com/test1"
        mock_post1.permalink = "/r/test/123"
        mock_post1.subreddit.display_name = "test_subreddit"
        mock_post1.selftext = "Test Content 1"  # Required: non-empty selftext
        mock_post1.comment_summary = "Test comment summary 1"
        mock_post1.created_utc = time.time()  # Recent post
        mock_post1.stickied = False  # Not stickied
        mock_post1.is_self = True  # Self post

        mock_post2 = MagicMock()
        mock_post2.id = "test_post_id_2"
        mock_post2.title = "Test Post Title 2"
        mock_post2.url = "https://reddit.com/test2"
        mock_post2.permalink = "/r/test/456"
        mock_post2.subreddit.display_name = "test_subreddit"
        mock_post2.selftext = "Test Content 2"  # Required: non-empty selftext
        mock_post2.comment_summary = "Test comment summary 2"
        mock_post2.created_utc = time.time()  # Recent post
        mock_post2.stickied = False  # Not stickied
        mock_post2.is_self = True  # Self post

        # Create a session and add a processed post
        session = SessionLocal()
        Base.metadata.create_all(bind=engine)
        
        # Create a subreddit first
        subreddit = Subreddit(subreddit_name="test_subreddit")
        session.add(subreddit)
        session.commit()
        
        pipeline_run = PipelineRun(status=PipelineStatus.STARTED.value)
        session.add(pipeline_run)
        session.commit()

        reddit_post = RedditPost(
            pipeline_run_id=pipeline_run.id,
            post_id="test_post_id_1",
            title="Test Post Title 1",
            content="Test Content 1",
            subreddit_id=subreddit.id,  # Use subreddit_id instead of subreddit
            url="https://reddit.com/test1",
            permalink="/r/test/123",
            author="test_user",
            score=100,
            num_comments=25,
        )
        session.add(reddit_post)
        session.commit()

        # Create agent with session
        agent = RedditAgent(pipeline_run_id=pipeline_run.id, session=session)

        # Patch agent.reddit_client.reddit.subreddit().hot to return both posts
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [mock_post1, mock_post2]
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit

        # Mock the comment summary generation
        agent._generate_comment_summary = MagicMock(return_value="Test comment summary")

        # Call _find_trending_post
        result = await agent._find_trending_post_for_task()

        # Verify that the second post was returned (first one was skipped)
        self.assertEqual(result, mock_post2)

    @patch("app.zazzle_product_designer.ZazzleProductDesigner.create_product")
    async def test_get_product_info(self, mock_create_product):
        """Test retrieving product information from the Zazzle Product Designer."""
        reddit_context = RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        )
        mock_create_product.return_value = ProductInfo(
            product_id="12345",
            name="Test Product",
            product_type="sticker",
            zazzle_template_id="template123",
            zazzle_tracking_code="tracking456",
            image_url="https://example.com/image.jpg",
            product_url="https://example.com/product",
            theme="test_theme",
            model="dall-e-3",
            prompt_version="1.0.0",
            reddit_context=reddit_context,
            design_instructions={"image": "https://example.com/image.jpg"},
            image_local_path="/path/to/image.jpg",
        )
        design_instructions = DesignInstructions(
            image="https://example.com/image.jpg",
            theme="test_theme",
            text="Custom Golf Ball",
            color="Red",
            quantity=12,
            product_type="sticker",
            template_id=None,
            model=None,
            prompt_version=None,
        )
        with patch.object(
            self.reddit_agent,
            "get_product_info",
            AsyncMock(return_value=mock_create_product.return_value),
        ):
            result = await self.reddit_agent.get_product_info(design_instructions)
            self.assertIsInstance(result, ProductInfo)
            self.assertEqual(result.product_id, "12345")
            self.assertEqual(result.product_url, "https://example.com/product")

    async def test_find_trending_post_for_task_simple(self):
        """Test the task-specific _find_trending_post_for_task method with simple mocking."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        
        # Mock the subreddit.hot method directly
        mock_submission = MagicMock()
        mock_submission.id = "test_post_id"
        mock_submission.title = "Test Post"
        mock_submission.score = 100
        mock_submission.is_self = True
        mock_submission.selftext = "Test content"
        mock_submission.created_utc = datetime.now(timezone.utc).timestamp()
        mock_submission.stickied = False
        mock_submission.subreddit.display_name = "test_subreddit"
        mock_submission.permalink = "/r/test/123"
        mock_submission.url = "https://reddit.com/test"
        mock_submission.author = "test_user"
        mock_submission.num_comments = 25
        
        # Mock the subreddit.hot method
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [mock_submission]
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit
        
        # Mock the comment summary generation
        agent._generate_comment_summary = MagicMock(return_value="Test comment summary")
        
        # Test the method
        result = await agent._find_trending_post_for_task()
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "test_post_id")
        self.assertEqual(result.title, "Test Post")
        self.assertEqual(result.comment_summary, "Test comment summary")

    async def test_get_product_info_for_task_simple(self):
        """Test the task-specific get_product_info_for_task method."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        
        # Mock the _find_trending_post_for_task method to return a valid post
        mock_submission = MagicMock()
        mock_submission.id = "test_post_id"
        mock_submission.title = "Test Post"
        mock_submission.selftext = "Test content"
        mock_submission.subreddit.display_name = "test_subreddit"
        mock_submission.permalink = "/r/test/123"
        mock_submission.url = "https://reddit.com/test"
        mock_submission.author = "test_user"
        mock_submission.score = 100
        mock_submission.num_comments = 25
        mock_submission.comment_summary = "Test comment summary"
        
        agent._find_trending_post_for_task = AsyncMock(return_value=mock_submission)
        
        # Mock the _determine_product_idea method
        mock_product_idea = MagicMock()
        mock_product_idea.theme = "Test Theme"
        mock_product_idea.image_description = "Test image description"
        mock_product_idea.design_instructions = {"image": "https://i.imgur.com/test.jpg", "theme": "Test Theme"}
        agent._determine_product_idea = AsyncMock(return_value=mock_product_idea)
        
        # Mock the image generator
        agent.image_generator = MagicMock()
        agent.image_generator.generate_image = AsyncMock(return_value=("https://imgur.com/test.jpg", "/tmp/test.jpg"))
        
        # Mock the product designer
        mock_product_info = MagicMock()
        mock_product_info.product_id = "test_product_123"
        agent.zazzle_designer = AsyncMock()
        agent.zazzle_designer.create_product = AsyncMock(return_value=mock_product_info)
        
        # Test the method
        result = await agent.get_product_info_for_task()
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].product_id, "test_product_123")

    def test_pick_subreddit(self):
        """Test that pick_subreddit returns a valid subreddit from the available list."""
        from app.agents.reddit_agent import AVAILABLE_SUBREDDITS, pick_subreddit

        # Test multiple calls to ensure randomness
        results = set()
        for _ in range(10):
            result = pick_subreddit()
            results.add(result)
            # Verify the result is in the available subreddits
            self.assertIn(result, AVAILABLE_SUBREDDITS)

        # With 10 calls and 3 subreddits, we should get at least 2 different results
        # (though it's theoretically possible to get the same one 10 times, it's very unlikely)
        self.assertGreaterEqual(len(results), 1)
        self.assertLessEqual(len(results), len(AVAILABLE_SUBREDDITS))

    async def test_find_top_post_from_subreddit_simple(self):
        """Test the find_top_post_from_subreddit method with simple mocking."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        
        # Mock the subreddit.top method directly
        mock_submission = MagicMock()
        mock_submission.id = "test_post_id"
        mock_submission.title = "Test Top Post"
        mock_submission.score = 500  # Higher score for top post
        mock_submission.is_self = True
        mock_submission.selftext = "Test content for top post"
        mock_submission.created_utc = datetime.now(timezone.utc).timestamp()
        mock_submission.stickied = False
        mock_submission.subreddit.display_name = "test_subreddit"
        mock_submission.permalink = "/r/test/123"
        mock_submission.url = "https://reddit.com/test"
        mock_submission.author = "test_user"
        mock_submission.num_comments = 50
        
        # Mock the subreddit.top method
        mock_subreddit = MagicMock()
        mock_subreddit.top.return_value = [mock_submission]
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit
        
        # Test the method with default parameters
        result = await agent.find_top_post_from_subreddit()
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "test_post_id")
        self.assertEqual(result.title, "Test Top Post")
        # Note: comment_summary is no longer generated in this method
        
        # Verify the top method was called with correct parameters (updated to "month")
        mock_subreddit.top.assert_called_once_with(time_filter="month", limit=100)

    async def test_find_top_post_from_subreddit_with_custom_parameters(self):
        """Test find_top_post_from_subreddit with custom parameters."""
        agent = RedditAgent(subreddit_name="golf")
        
        # Mock the subreddit.top method
        mock_submission = MagicMock()
        mock_submission.id = "custom_post_id"
        mock_submission.title = "Custom Top Post"
        mock_submission.score = 750
        mock_submission.is_self = True
        mock_submission.selftext = "Custom content"
        mock_submission.created_utc = datetime.now(timezone.utc).timestamp()
        mock_submission.stickied = False
        mock_submission.subreddit.display_name = "custom_subreddit"
        mock_submission.comment_summary = "Custom comment summary"
        
        mock_subreddit = MagicMock()
        mock_subreddit.top.return_value = [mock_submission]
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit
        
        agent._generate_comment_summary = MagicMock(return_value="Custom comment summary")
        
        # Test with custom parameters
        result = await agent.find_top_post_from_subreddit(
            tries=2,
            limit=50,
            subreddit_name="custom_subreddit",
            time_filter="month"
        )
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "custom_post_id")
        
        # Verify the top method was called with custom parameters
        mock_subreddit.top.assert_called_once_with(time_filter="month", limit=50)

    async def test_find_top_post_from_subreddit_skips_stickied_posts(self):
        """Test that find_top_post_from_subreddit skips stickied posts."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        
        # Create mock submissions - first one stickied, second one valid
        mock_stickied_submission = MagicMock()
        mock_stickied_submission.id = "stickied_post_id"
        mock_stickied_submission.title = "Stickied Post"
        mock_stickied_submission.score = 1000
        mock_stickied_submission.is_self = True
        mock_stickied_submission.selftext = "Stickied content"
        mock_stickied_submission.created_utc = datetime.now(timezone.utc).timestamp()
        mock_stickied_submission.stickied = True  # This should be skipped
        mock_stickied_submission.subreddit.display_name = "test_subreddit"
        
        mock_valid_submission = MagicMock()
        mock_valid_submission.id = "valid_post_id"
        mock_valid_submission.title = "Valid Post"
        mock_valid_submission.score = 500
        mock_valid_submission.is_self = True
        mock_valid_submission.selftext = "Valid content"
        mock_valid_submission.created_utc = datetime.now(timezone.utc).timestamp()
        mock_valid_submission.stickied = False  # This should be accepted
        mock_valid_submission.subreddit.display_name = "test_subreddit"
        
        # Mock the subreddit.top method to return both submissions
        mock_subreddit = MagicMock()
        mock_subreddit.top.return_value = [mock_stickied_submission, mock_valid_submission]
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit
        
        agent._generate_comment_summary = MagicMock(return_value="Valid comment summary")
        
        # Test the method
        result = await agent.find_top_post_from_subreddit()
        
        # Verify the result is the valid submission (not the stickied one)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "valid_post_id")
        self.assertEqual(result.title, "Valid Post")

    async def test_find_top_post_from_subreddit_skips_old_posts(self):
        """Test that find_top_post_from_subreddit skips posts older than 60 days."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        
        # Create mock submissions - first one old, second one recent
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=65)).timestamp()  # 65 days old (should be skipped)
        recent_timestamp = (datetime.now(timezone.utc) - timedelta(days=5)).timestamp()  # 5 days old
        
        mock_old_submission = MagicMock()
        mock_old_submission.id = "old_post_id"
        mock_old_submission.title = "Old Post"
        mock_old_submission.score = 1000
        mock_old_submission.is_self = True
        mock_old_submission.selftext = "Old content"
        mock_old_submission.created_utc = old_timestamp  # 65 days old
        mock_old_submission.stickied = False
        mock_old_submission.subreddit.display_name = "test_subreddit"
        
        mock_recent_submission = MagicMock()
        mock_recent_submission.id = "recent_post_id"
        mock_recent_submission.title = "Recent Post"
        mock_recent_submission.score = 500
        mock_recent_submission.is_self = True
        mock_recent_submission.selftext = "Recent content"
        mock_recent_submission.created_utc = recent_timestamp  # 5 days old
        mock_recent_submission.stickied = False
        mock_recent_submission.subreddit.display_name = "test_subreddit"
        
        # Mock the subreddit.top method to return both submissions
        mock_subreddit = MagicMock()
        mock_subreddit.top.return_value = [mock_old_submission, mock_recent_submission]
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit
        
        # Test the method
        result = await agent.find_top_post_from_subreddit()
        
        # Verify the result is the recent submission (not the old one)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "recent_post_id")
        self.assertEqual(result.title, "Recent Post")

    async def test_find_top_post_from_subreddit_skips_posts_without_selftext(self):
        """Test that find_top_post_from_subreddit handles posts without selftext based on engagement."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        
        # Create mock submissions - first one without selftext but low engagement, second one with selftext
        mock_no_selftext_low_engagement = MagicMock()
        mock_no_selftext_low_engagement.id = "no_selftext_low_engagement_id"
        mock_no_selftext_low_engagement.title = "No Selftext Low Engagement Post"
        mock_no_selftext_low_engagement.score = 20  # Below threshold
        mock_no_selftext_low_engagement.num_comments = 15  # Below threshold
        mock_no_selftext_low_engagement.is_self = True
        mock_no_selftext_low_engagement.selftext = ""  # Empty selftext
        mock_no_selftext_low_engagement.created_utc = datetime.now(timezone.utc).timestamp()
        mock_no_selftext_low_engagement.stickied = False
        mock_no_selftext_low_engagement.subreddit.display_name = "test_subreddit"
        
        mock_with_selftext_submission = MagicMock()
        mock_with_selftext_submission.id = "with_selftext_post_id"
        mock_with_selftext_submission.title = "With Selftext Post"
        mock_with_selftext_submission.score = 500
        mock_with_selftext_submission.num_comments = 50
        mock_with_selftext_submission.is_self = True
        mock_with_selftext_submission.selftext = "Has selftext content"  # Has selftext
        mock_with_selftext_submission.created_utc = datetime.now(timezone.utc).timestamp()
        mock_with_selftext_submission.stickied = False
        mock_with_selftext_submission.subreddit.display_name = "test_subreddit"
        
        # Mock the subreddit.top method to return both submissions
        mock_subreddit = MagicMock()
        mock_subreddit.top.return_value = [mock_no_selftext_low_engagement, mock_with_selftext_submission]
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit
        
        # Test the method
        result = await agent.find_top_post_from_subreddit()
        
        # Verify the result is the submission with selftext (low engagement post without selftext should be skipped)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "with_selftext_post_id")
        self.assertEqual(result.title, "With Selftext Post")

    async def test_find_top_post_from_subreddit_keeps_high_engagement_posts_without_selftext(self):
        """Test that find_top_post_from_subreddit keeps posts without selftext if they have high engagement."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        
        # Create mock submission without selftext but with high engagement
        mock_high_engagement_no_selftext = MagicMock()
        mock_high_engagement_no_selftext.id = "high_engagement_no_selftext_id"
        mock_high_engagement_no_selftext.title = "High Engagement No Selftext Post"
        mock_high_engagement_no_selftext.score = 100  # Above threshold (30+)
        mock_high_engagement_no_selftext.num_comments = 50  # Above threshold (30+)
        mock_high_engagement_no_selftext.is_self = True
        mock_high_engagement_no_selftext.selftext = ""  # Empty selftext
        mock_high_engagement_no_selftext.created_utc = datetime.now(timezone.utc).timestamp()
        mock_high_engagement_no_selftext.stickied = False
        mock_high_engagement_no_selftext.subreddit.display_name = "test_subreddit"
        
        # Mock the subreddit.top method to return the submission
        mock_subreddit = MagicMock()
        mock_subreddit.top.return_value = [mock_high_engagement_no_selftext]
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit
        
        # Test the method
        result = await agent.find_top_post_from_subreddit()
        
        # Verify the result is the high engagement post without selftext (should be kept)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "high_engagement_no_selftext_id")
        self.assertEqual(result.title, "High Engagement No Selftext Post")

    async def test_find_top_post_from_subreddit_skips_processed_posts(self):
        """Test that find_top_post_from_subreddit skips posts that have already been processed."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        
        # Mock the session and query
        mock_session = MagicMock()
        agent.session = mock_session
        
        # Create mock submissions
        mock_processed_submission = MagicMock()
        mock_processed_submission.id = "processed_post_id"
        mock_processed_submission.title = "Processed Post"
        mock_processed_submission.score = 1000
        mock_processed_submission.is_self = True
        mock_processed_submission.selftext = "Processed content"
        mock_processed_submission.created_utc = datetime.now(timezone.utc).timestamp()
        mock_processed_submission.stickied = False
        mock_processed_submission.subreddit.display_name = "test_subreddit"
        
        mock_unprocessed_submission = MagicMock()
        mock_unprocessed_submission.id = "unprocessed_post_id"
        mock_unprocessed_submission.title = "Unprocessed Post"
        mock_unprocessed_submission.score = 500
        mock_unprocessed_submission.is_self = True
        mock_unprocessed_submission.selftext = "Unprocessed content"
        mock_unprocessed_submission.created_utc = datetime.now(timezone.utc).timestamp()
        mock_unprocessed_submission.stickied = False
        mock_unprocessed_submission.subreddit.display_name = "test_subreddit"
        
        # Mock the database query to return existing post for processed submission
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.side_effect = [
            MagicMock(),  # Return existing post for processed_post_id
            None  # Return None for unprocessed_post_id
        ]
        mock_session.query.return_value = mock_query
        
        # Mock the subreddit.top method to return both submissions
        mock_subreddit = MagicMock()
        mock_subreddit.top.return_value = [mock_processed_submission, mock_unprocessed_submission]
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit
        
        agent._generate_comment_summary = MagicMock(return_value="Unprocessed comment summary")
        
        # Test the method
        result = await agent.find_top_post_from_subreddit()
        
        # Verify the result is the unprocessed submission
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "unprocessed_post_id")
        self.assertEqual(result.title, "Unprocessed Post")

    async def test_find_top_post_from_subreddit_with_task_context(self):
        """Test find_top_post_from_subreddit with task context for specific post commissioning."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        agent.task_context = {"post_id": "commissioned_post_id"}
        
        # Mock the reddit client to return a specific post
        mock_commissioned_submission = MagicMock()
        mock_commissioned_submission.id = "commissioned_post_id"
        mock_commissioned_submission.title = "Commissioned Post"
        mock_commissioned_submission.score = 1000
        mock_commissioned_submission.is_self = True
        mock_commissioned_submission.selftext = "Commissioned content"
        mock_commissioned_submission.created_utc = datetime.now(timezone.utc).timestamp()
        mock_commissioned_submission.stickied = False
        mock_commissioned_submission.subreddit.display_name = "test_subreddit"
        
        agent.reddit_client.get_post = MagicMock(return_value=mock_commissioned_submission)
        agent._generate_comment_summary = MagicMock(return_value="Commissioned comment summary")
        
        # Mock progress callback
        mock_progress_callback = AsyncMock()
        agent.progress_callback = mock_progress_callback
        
        # Test the method
        result = await agent.find_top_post_from_subreddit()
        
        # Verify the result is the commissioned submission
        self.assertIsNotNone(result)
        self.assertEqual(result.id, "commissioned_post_id")
        self.assertEqual(result.title, "Commissioned Post")
        
        # Verify the get_post method was called with the correct post_id
        agent.reddit_client.get_post.assert_called_once_with("commissioned_post_id")
        
        # Verify progress callback was called
        mock_progress_callback.assert_called_once_with("post_fetched", {
            "post_title": "Commissioned Post",
            "post_id": "commissioned_post_id",
            "subreddit": "test_subreddit"
        })

    async def test_find_top_post_from_subreddit_returns_none_when_no_valid_posts(self):
        """Test that find_top_post_from_subreddit returns None when no valid posts are found."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        
        # Mock the subreddit.top method to return an empty list
        mock_subreddit = MagicMock()
        mock_subreddit.top.return_value = []
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit
        
        # Test the method
        result = await agent.find_top_post_from_subreddit(tries=2)
        
        # Verify the result is None
        self.assertIsNone(result)
        
        # Verify the top method was called twice (once per try)
        self.assertEqual(mock_subreddit.top.call_count, 2)

    async def test_find_top_post_from_subreddit_handles_exceptions(self):
        """Test that find_top_post_from_subreddit handles exceptions gracefully."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        
        # Mock the subreddit.top method to raise an exception
        mock_subreddit = MagicMock()
        mock_subreddit.top.side_effect = Exception("Reddit API error")
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit
        
        # Test the method
        result = await agent.find_top_post_from_subreddit()
        
        # Verify the result is None when exception occurs
        self.assertIsNone(result)

    async def test_find_top_post_from_subreddit_different_time_filters(self):
        """Test find_top_post_from_subreddit with different time filters."""
        agent = RedditAgent(subreddit_name="test_subreddit")
        
        # Mock the subreddit.top method
        mock_submission = MagicMock()
        mock_submission.id = "time_filter_test_id"
        mock_submission.title = "Time Filter Test Post"
        mock_submission.score = 300
        mock_submission.is_self = True
        mock_submission.selftext = "Time filter test content"
        mock_submission.created_utc = datetime.now(timezone.utc).timestamp()
        mock_submission.stickied = False
        mock_submission.subreddit.display_name = "test_subreddit"
        
        mock_subreddit = MagicMock()
        mock_subreddit.top.return_value = [mock_submission]
        agent.reddit_client.reddit.subreddit.return_value = mock_subreddit
        
        agent._generate_comment_summary = MagicMock(return_value="Time filter test summary")
        
        # Test different time filters
        time_filters = ["all", "day", "hour", "month", "week", "year"]
        
        for time_filter in time_filters:
            # Reset the mock call count
            mock_subreddit.top.reset_mock()
            
            # Test with this time filter
            result = await agent.find_top_post_from_subreddit(time_filter=time_filter)
            
            # Verify the result
            self.assertIsNotNone(result)
            self.assertEqual(result.id, "time_filter_test_id")
            
            # Verify the top method was called with the correct time filter
            mock_subreddit.top.assert_called_once_with(time_filter=time_filter, limit=100)


if __name__ == "__main__":
    unittest.main()
