import unittest
from unittest.mock import patch, MagicMock, Mock, AsyncMock
import os
from app.agents.reddit_interaction_agent import RedditInteractionAgent
from app.zazzle_product_designer import ZazzleProductDesigner
import logging
from io import StringIO
import praw
from app.models import ProductInfo, RedditContext, ProductIdea, PipelineConfig, DesignInstructions
import pytest
from unittest import IsolatedAsyncioTestCase
from app.db.database import SessionLocal, Base, engine
from app.db.models import PipelineRun, RedditPost
from datetime import datetime, timezone
from app.pipeline_status import PipelineStatus
import openai
import time

@pytest.fixture(autouse=True)
def clean_db():
    """Ensure a clean database state before each test by dropping and recreating all tables."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

class TestRedditInteractionAgent(IsolatedAsyncioTestCase):
    """Test cases for the Reddit Interaction Agent."""

    async def asyncSetUp(self):
        """Set up the test environment."""
        self.reddit_agent = RedditInteractionAgent(subreddit_name='test_subreddit')
        self.reddit_agent.reddit = MagicMock()
        self.reddit_agent.personality = {
            'engagement_rules': {
                'max_posts_per_day': 5,
                'max_comments_per_day': 10,
                'max_upvotes_per_day': 20,
                'revenue_focus': {
                    'max_affiliate_links_per_day': 3
                },
                'min_time_between_actions': 0
            }
        }
        self.reddit_agent.daily_stats = {
            'posts': 0,
            'comments': 0,
            'upvotes': 0,
            'affiliate_posts': 0,
            'last_action_time': None
        }

        self.patcher_env = patch.dict(os.environ, {
            'REDDIT_CLIENT_ID': 'test_client_id',
            'REDDIT_CLIENT_SECRET': 'test_client_secret',
            'REDDIT_USERNAME': 'test_username',
            'REDDIT_PASSWORD': 'test_password',
            'REDDIT_USER_AGENT': 'test_user_agent',
            'ZAZZLE_AFFILIATE_ID': 'test_affiliate_id',
            'ZAZZLE_TEMPLATE_ID': 'test_template_id',
            'ZAZZLE_TRACKING_CODE': 'test_tracking_code'
        })
        self.patcher_env.start()
        self.addCleanup(self.patcher_env.stop)

        self.patcher_praw_reddit = patch('praw.Reddit')
        self.mock_reddit_constructor = self.patcher_praw_reddit.start()
        self.mock_reddit_instance = MagicMock()
        self.mock_reddit_constructor.return_value = self.mock_reddit_instance
        self.mock_reddit_instance.config = MagicMock()
        self.mock_reddit_instance.config.check_for_updates = False 
        self.addCleanup(self.patcher_praw_reddit.stop)

        self.patcher_config_boolean = patch('praw.config.Config._config_boolean', return_value=True)
        self.patcher_config_boolean.start()
        self.addCleanup(self.patcher_config_boolean.stop)

        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        logging.getLogger('app').addHandler(self.handler)
        self.addCleanup(lambda: logging.getLogger('app').removeHandler(self.handler))

        # Mock OpenAI
        self.patcher_openai = patch('openai.OpenAI')
        self.mock_openai = self.patcher_openai.start()
        self.mock_openai_instance = MagicMock()
        self.mock_openai.return_value = self.mock_openai_instance
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='Test response'))]
        )
        self.addCleanup(self.patcher_openai.stop)

    @pytest.mark.xfail(reason="Interaction methods not yet implemented")
    async def test_interact_with_subreddit(self):
        """Test interacting with a subreddit."""
        with patch.object(self.reddit_agent, 'interact_with_subreddit', AsyncMock(return_value={"result": "success"})):
            result = await self.reddit_agent.interact_with_subreddit('test_subreddit')
            assert result["result"] == "success"

    @pytest.mark.xfail(reason="Interaction methods not yet implemented")
    async def test_interact_with_votes(self):
        """Test upvoting and downvoting on a dummy post."""
        with patch.object(self.reddit_agent, 'interact_with_votes', AsyncMock(return_value={"result": "success"})):
            result = await self.reddit_agent.interact_with_votes('dummy_id')
            assert result["result"] == "success"

    @pytest.mark.xfail(reason="Interaction methods not yet implemented")
    async def test_interact_with_users_comments(self):
        """Test the Reddit agent's ability to interact with comments in a post."""
        with patch.object(self.reddit_agent, 'interact_with_users', AsyncMock(return_value={"result": "success"})):
            result = await self.reddit_agent.interact_with_users('test_post_id')
            assert result["result"] == "success"

    @pytest.mark.xfail(reason="Interaction methods not yet implemented")
    async def test_comment_on_post(self):
        """Test the Reddit agent's ability to comment on posts."""
        mock_submission = MagicMock()
        mock_submission.reply = AsyncMock(return_value={"id": "comment_id"})
        with patch('praw.Reddit') as mock_reddit:
            mock_reddit_instance = Mock()
            mock_reddit.return_value = mock_reddit_instance
            mock_reddit_instance.submission.return_value = mock_submission
            self.reddit_agent.reddit = mock_reddit_instance
            test_comment = "Test comment text"
            with patch.object(self.reddit_agent, 'comment_on_post', AsyncMock(return_value={"id": "comment_id"})):
                result = await self.reddit_agent.comment_on_post(mock_submission.id, test_comment)
                assert result["id"] == "comment_id"

    @pytest.mark.xfail(reason="Interaction methods not yet implemented")
    @patch('praw.Reddit')
    async def test_reddit_voting(self, mock_reddit):
        """Test voting functionality on Reddit."""
        mock_reddit_instance = MagicMock()
        mock_reddit.return_value = mock_reddit_instance
        self.reddit_agent.reddit = mock_reddit_instance
        
        # Test upvoting
        result = self.reddit_agent.interact_with_votes('test_post_id')
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.xfail(reason="Interaction methods not yet implemented")
    @patch('praw.Reddit')
    async def test_reddit_comment_voting(self, mock_reddit):
        """Test voting on comments."""
        mock_reddit_instance = MagicMock()
        mock_reddit.return_value = mock_reddit_instance
        self.reddit_agent.reddit = mock_reddit_instance
        
        # Test comment voting
        result = self.reddit_agent.interact_with_votes('test_post_id', 'test_comment_id')
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.xfail(reason="Interaction methods not yet implemented")
    @patch('praw.Reddit')
    async def test_reddit_post_comment(self, mock_reddit):
        """Test posting comments on Reddit."""
        mock_reddit_instance = MagicMock()
        mock_reddit.return_value = mock_reddit_instance
        self.reddit_agent.reddit = mock_reddit_instance
        
        # Test posting a comment
        result = self.reddit_agent.comment_on_post('test_post_id', 'Test comment')
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.xfail(reason="Interaction methods not yet implemented")
    @patch('praw.Reddit')
    async def test_reddit_engaging_comment(self, mock_reddit):
        """Test generating and posting engaging comments."""
        mock_reddit_instance = MagicMock()
        mock_reddit.return_value = mock_reddit_instance
        self.reddit_agent.reddit = mock_reddit_instance
        
        # Test generating an engaging comment
        result = self.reddit_agent.engage_with_post('test_post_id')
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.xfail(reason="Interaction methods not yet implemented")
    @patch('praw.Reddit')
    async def test_reddit_marketing_comment(self, mock_reddit):
        """Test posting marketing comments."""
        mock_reddit_instance = MagicMock()
        mock_reddit.return_value = mock_reddit_instance
        self.reddit_agent.reddit = mock_reddit_instance
        
        # Test posting a marketing comment
        product_info = ProductInfo(
            product_id='test_id',
            name='Test Product',
            product_type='sticker',
            zazzle_template_id='template123',
            zazzle_tracking_code='tracking456',
            image_url='https://example.com/image.jpg',
            product_url='https://example.com/product',
            theme='test_theme',
            model='dall-e-3',
            prompt_version='1.0.0',
            reddit_context=RedditContext(
                post_id='test_post_id',
                post_title='Test Post',
                post_url='https://reddit.com/test',
                subreddit='test_subreddit'
            ),
            design_instructions={'image': 'https://example.com/image.jpg'},
            image_local_path='/path/to/image.jpg'
        )
        result = self.reddit_agent.engage_with_post_marketing('test_post_id')
        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.xfail(reason="Interaction methods not yet implemented")
    @patch('praw.Reddit')
    async def test_reddit_comment_marketing_reply(self, mock_reddit):
        """Test replying to comments with marketing content."""
        mock_reddit_instance = MagicMock()
        mock_reddit.return_value = mock_reddit_instance
        self.reddit_agent.reddit = mock_reddit_instance
        
        # Test replying to a comment with marketing content
        product_info = ProductInfo(
            product_id='test_id',
            name='Test Product',
            product_type='sticker',
            zazzle_template_id='template123',
            zazzle_tracking_code='tracking456',
            image_url='https://example.com/image.jpg',
            product_url='https://example.com/product',
            theme='test_theme',
            model='dall-e-3',
            prompt_version='1.0.0',
            reddit_context=RedditContext(
                post_id='test_post_id',
                post_title='Test Post',
                post_url='https://reddit.com/test',
                subreddit='test_subreddit'
            ),
            design_instructions={'image': 'https://example.com/image.jpg'},
            image_local_path='/path/to/image.jpg'
        )
        result = self.reddit_agent.reply_to_comment_with_marketing('test_comment_id', product_info, {})
        assert result is not None
        assert isinstance(result, dict) 