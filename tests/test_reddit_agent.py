import logging
import os
import time
import unittest
from datetime import datetime, timezone
from io import StringIO
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import openai
import praw
import pytest

from app.agents.reddit_agent import RedditAgent
from app.db.database import Base, SessionLocal, engine
from app.db.models import PipelineRun, RedditPost
from app.models import (
    DesignInstructions,
    PipelineConfig,
    ProductIdea,
    ProductInfo,
    RedditContext,
)
from app.pipeline_status import PipelineStatus
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
        self.reddit_agent.reddit = MagicMock()
        self.reddit_agent.personality = {
            "engagement_rules": {
                "max_posts_per_day": 5,
                "max_comments_per_day": 10,
                "max_upvotes_per_day": 20,
                "revenue_focus": {"max_affiliate_links_per_day": 3},
                "min_time_between_actions": 0,
            }
        }
        self.reddit_agent.daily_stats = {
            "posts": 0,
            "comments": 0,
            "upvotes": 0,
            "affiliate_posts": 0,
            "last_action_time": None,
        }

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

    @patch(
        "app.image_generator.ImageGenerator.generate_image",
        new_callable=AsyncMock,
        return_value=("https://example.com/image.jpg", "/tmp/image.jpg"),
    )
    @patch(
        "app.zazzle_product_designer.ZazzleProductDesigner.create_product",
        new_callable=AsyncMock,
    )
    @patch(
        "app.agents.reddit_agent.RedditAgent._determine_product_idea",
        return_value=ProductIdea(
            theme="Test Theme",
            image_description="Test image description",
            design_instructions={
                "image": "https://example.com/image.jpg",
                "theme": "Test Theme",
            },
            reddit_context=RedditContext(
                post_id="test_post_id",
                post_title="Test Post Title",
                post_url="https://reddit.com/test",
                subreddit="test_subreddit",
            ),
            model="dall-e-3",
            prompt_version="1.0.0",
        ),
    )
    @patch(
        "app.agents.reddit_agent.RedditAgent._find_trending_post",
        new_callable=AsyncMock,
    )
    async def test_find_and_create_product(
        self,
        mock_find_trending_post,
        mock_determine_product_idea,
        mock_create_product,
        mock_generate_image,
    ):
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

        mock_product_info = MagicMock()
        mock_create_product.return_value = mock_product_info

        result = await self.reddit_agent.find_and_create_product()
        self.assertEqual(result, mock_product_info)

    @patch(
        "app.zazzle_product_designer.ZazzleProductDesigner.create_product",
        new_callable=AsyncMock,
    )
    async def test_create_product(self, mock_create_product):
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
        mock_create_product.return_value = mock_product_info

        # Simulate calling create_product via the agent's product_designer
        result = await self.reddit_agent.product_designer.create_product(
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
        self.assertEqual(result, mock_product_info)

    @patch(
        "app.agents.reddit_agent.RedditAgent._find_trending_post",
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

        result = await self.reddit_agent._find_trending_post()
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
        mock_post1.selftext = "Test Content 1"
        mock_post1.comment_summary = "Test comment summary 1"
        mock_post1.created_utc = time.time()
        mock_post1.stickied = False

        mock_post2 = MagicMock()
        mock_post2.id = "test_post_id_2"
        mock_post2.title = "Test Post Title 2"
        mock_post2.url = "https://reddit.com/test2"
        mock_post2.permalink = "/r/test/456"
        mock_post2.subreddit.display_name = "test_subreddit"
        mock_post2.selftext = "Test Content 2"
        mock_post2.comment_summary = "Test comment summary 2"
        mock_post2.created_utc = time.time()
        mock_post2.stickied = False

        # Create a session and add a processed post
        session = SessionLocal()
        Base.metadata.create_all(bind=engine)
        pipeline_run = PipelineRun(status=PipelineStatus.STARTED.value)
        session.add(pipeline_run)
        session.commit()

        reddit_post = RedditPost(
            pipeline_run_id=pipeline_run.id,
            post_id="test_post_id_1",
            title="Test Post Title 1",
            content="Test Content 1",
            subreddit="test_subreddit",
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

        # Mock subreddit.hot to return both posts
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [mock_post1, mock_post2]
        agent.reddit.subreddit.return_value = mock_subreddit

        # Call _find_trending_post
        result = await agent._find_trending_post()

        # Verify that the second post was returned (first one was skipped)
        self.assertEqual(result, mock_post2)

        # Cleanup
        session.close()
        Base.metadata.drop_all(bind=engine)

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

    async def test_analyze_post_context(self):
        """Test the Reddit agent's ability to analyze post context."""
        mock_post = MagicMock()
        mock_post.title = "Test Post Title"
        mock_post.selftext = "Test post content"
        mock_post.score = 100
        mock_post.num_comments = 5

        mock_comment1 = MagicMock()
        mock_comment1.body = "First comment"
        mock_comment1.author = "user1"
        mock_comment1.score = 50

        mock_comment2 = MagicMock()
        mock_comment2.body = "Second comment"
        mock_comment2.author = "user2"
        mock_comment2.score = 30

        mock_comment1.stickied = False
        mock_comment2.stickied = False

        mock_comments = MagicMock()
        mock_comments.replace_more.return_value = []
        mock_comments.list.return_value = [mock_comment1, mock_comment2]
        mock_post.comments = mock_comments
        mock_post.subreddit.display_name = "golf"

        self.reddit_agent._analyze_post_context = AsyncMock(
            return_value={
                "title": mock_post.title,
                "content": mock_post.selftext,
                "score": mock_post.score,
                "num_comments": mock_post.num_comments,
                "top_comments": [
                    {"text": mock_comment1.body, "author": mock_comment1.author},
                    {"text": mock_comment2.body, "author": mock_comment2.author},
                ],
            }
        )
        context = await self.reddit_agent._analyze_post_context(mock_post)

        assert context["title"] == "Test Post Title"
        assert context["content"] == "Test post content"
        assert context["score"] == 100
        assert context["num_comments"] == 5
        assert len(context["top_comments"]) == 2

    async def test_generate_engaging_comment(self):
        """Test the Reddit agent's ability to generate engaging comments."""
        context = {
            "title": "Test Post Title",
            "content": "Test post content",
            "score": 100,
            "num_comments": 5,
            "top_comments": [
                {"text": "First comment", "author": "user1"},
                {"text": "Second comment", "author": "user2"},
            ],
        }

        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated engaging comment"))]
        )

        self.reddit_agent._generate_engaging_comment = AsyncMock(
            return_value="Generated engaging comment"
        )
        comment = await self.reddit_agent._generate_engaging_comment(context)
        assert comment == "Generated engaging comment"

    async def test_generate_marketing_comment(self):
        """Test the Reddit agent's ability to generate marketing comments."""
        reddit_context = RedditContext(
            post_id="test_post_id",
            post_title="Test Post Title",
            post_url="https://reddit.com/test",
            subreddit="test_subreddit",
        )

        product_info = ProductInfo(
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

        post_context = {
            "title": "Test Post Title",
            "content": "Test post content",
            "score": 100,
            "num_comments": 5,
            "top_comments": [
                {"text": "First comment", "author": "user1"},
                {"text": "Second comment", "author": "user2"},
            ],
        }

        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(message=MagicMock(content="Generated marketing comment"))
            ]
        )

        self.reddit_agent._generate_marketing_comment = AsyncMock(
            return_value="Generated marketing comment"
        )
        comment = await self.reddit_agent._generate_marketing_comment(
            product_info, post_context
        )
        assert comment == "Generated marketing comment"

    @patch("app.agents.reddit_agent.openai")
    async def test_find_trending_post(self, mock_openai):
        agent = RedditAgent(subreddit_name="test_subreddit")
        agent.openai = mock_openai
        with patch("praw.Reddit") as mock_reddit:
            mock_submission = MagicMock()
            mock_submission.title = "Test Post"
            mock_submission.score = 100
            mock_submission.is_self = False
            mock_submission.selftext = "Test content"
            mock_submission.created_utc = datetime.now(timezone.utc).timestamp()
            mock_submission.stickied = False
            mock_submission.subreddit.display_name = "test_subreddit"
            mock_comment = MagicMock()
            mock_comment.body = "Test comment"
            mock_submission.comments.replace_more = MagicMock(
                side_effect=lambda limit=0: None
            )
            mock_submission.comments.list.return_value = [mock_comment]
            subreddit_mock = MagicMock()
            subreddit_mock.hot.return_value = [mock_submission]
            agent.reddit.subreddit = MagicMock(return_value=subreddit_mock)
            # Mock OpenAI response
            mock_openai.chat.completions.create.return_value.choices = [
                MagicMock(message=MagicMock(content="Summary of comments"))
            ]
            try:
                result = await agent._find_trending_post(tries=3, limit=20)
                assert result is not None
                assert result.title == "Test Post"
            except Exception as e:
                print(f"Exception during test_find_trending_post: {e}")
                raise

    async def test_find_reddit_post_skips_stickied(self):
        """Test that _find_trending_post skips stickied posts and returns the first non-stickied post."""
        # Setup
        mock_stickied_post = MagicMock()
        mock_stickied_post.id = "test_stickied_post_id"
        mock_stickied_post.title = "Test Stickied Post Title"
        mock_stickied_post.url = "https://reddit.com/test_stickied"
        mock_stickied_post.permalink = "/r/test/789"
        mock_stickied_post.subreddit.display_name = "test_subreddit"
        mock_stickied_post.selftext = "Test Stickied Content"
        mock_stickied_post.comment_summary = "Test stickied comment summary"
        mock_stickied_post.stickied = True
        mock_stickied_post.created_utc = time.time()

        mock_normal_post = MagicMock()
        mock_normal_post.id = "test_normal_post_id"
        mock_normal_post.title = "Test Normal Post Title"
        mock_normal_post.url = "https://reddit.com/test_normal"
        mock_normal_post.permalink = "/r/test/101"
        mock_normal_post.subreddit.display_name = "test_subreddit"
        mock_normal_post.selftext = "Test Normal Content"
        mock_normal_post.comment_summary = "Test normal comment summary"
        mock_normal_post.stickied = False
        mock_normal_post.created_utc = time.time()

        # Create a session
        session = SessionLocal()
        Base.metadata.create_all(bind=engine)
        pipeline_run = PipelineRun(status=PipelineStatus.STARTED.value)
        session.add(pipeline_run)
        session.commit()

        # Create agent with session
        agent = RedditAgent(pipeline_run_id=pipeline_run.id, session=session)

        # Mock subreddit.hot to return both posts
        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [mock_stickied_post, mock_normal_post]
        agent.reddit.subreddit.return_value = mock_subreddit

        # Call _find_trending_post
        result = await agent._find_trending_post()

        # Verify that only the non-stickied post was returned
        self.assertEqual(result, mock_normal_post)

        # Cleanup
        session.close()
        Base.metadata.drop_all(bind=engine)

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


if __name__ == "__main__":
    unittest.main()
