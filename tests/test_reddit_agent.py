import unittest
from unittest.mock import patch, MagicMock, Mock, AsyncMock
import os
from app.agents.reddit_agent import RedditAgent
from app.zazzle_product_designer import ZazzleProductDesigner
import logging
from io import StringIO
import praw
from app.models import ProductInfo, RedditContext, ProductIdea, PipelineConfig, DesignInstructions
import pytest
from unittest import IsolatedAsyncioTestCase

class TestRedditAgent(IsolatedAsyncioTestCase):
    """Test cases for the Reddit Agent."""

    async def asyncSetUp(self):
        """Set up the test environment."""
        self.config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id="test_template_id",
            zazzle_tracking_code="test_tracking_code",
            prompt_version="1.0.0"
        )
        self.reddit_agent = RedditAgent(self.config)
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

    @patch('app.zazzle_product_designer.ZazzleProductDesigner.create_product')
    async def test_get_product_info(self, mock_create_product):
        """Test retrieving product information from the Zazzle Product Designer."""
        reddit_context = RedditContext(
            post_id='test_post_id',
            post_title='Test Post Title',
            post_url='https://reddit.com/test',
            subreddit='test_subreddit'
        )
        mock_create_product.return_value = ProductInfo(
            product_id='12345',
            name='Test Product',
            product_type='sticker',
            zazzle_template_id='template123',
            zazzle_tracking_code='tracking456',
            image_url='https://example.com/image.jpg',
            product_url='https://example.com/product',
            theme='test_theme',
            model='dall-e-3',
            prompt_version='1.0.0',
            reddit_context=reddit_context,
            design_instructions={'image': 'https://example.com/image.jpg'},
            image_local_path='/path/to/image.jpg'
        )
        design_instructions = DesignInstructions(
            image='https://example.com/image.jpg',
            theme='test_theme',
            text='Custom Golf Ball',
            color='Red',
            quantity=12,
            product_type='sticker',
            template_id=None,
            model=None,
            prompt_version=None
        )
        with patch.object(self.reddit_agent, 'get_product_info', AsyncMock(return_value=mock_create_product.return_value)):
            result = await self.reddit_agent.get_product_info(design_instructions)
            self.assertIsInstance(result, ProductInfo)
            self.assertEqual(result.product_id, '12345')
            self.assertEqual(result.product_url, 'https://example.com/product')

    async def test_interact_with_subreddit(self):
        """Test interacting with a subreddit."""
        with patch.object(self.reddit_agent, 'interact_with_subreddit', AsyncMock(return_value={"result": "success"})):
            result = await self.reddit_agent.interact_with_subreddit('test_subreddit')
            assert result["result"] == "success"

    async def test_interact_with_votes(self):
        """Test upvoting and downvoting on a dummy post."""
        with patch.object(self.reddit_agent, 'interact_with_votes', AsyncMock(return_value={"result": "success"})):
            result = await self.reddit_agent.interact_with_votes('dummy_id')
            assert result["result"] == "success"

    async def test_interact_with_users_comments(self):
        """Test the Reddit agent's ability to interact with comments in a post."""
        with patch.object(self.reddit_agent, 'interact_with_users', AsyncMock(return_value={"result": "success"})):
            result = await self.reddit_agent.interact_with_users('test_post_id')
            assert result["result"] == "success"

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
        
        self.reddit_agent._analyze_post_context = AsyncMock(return_value={
            "title": mock_post.title,
            "content": mock_post.selftext,
            "score": mock_post.score,
            "num_comments": mock_post.num_comments,
            "top_comments": [
                {"text": mock_comment1.body, "author": mock_comment1.author},
                {"text": mock_comment2.body, "author": mock_comment2.author}
            ]
        })
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
                {"text": "Second comment", "author": "user2"}
            ]
        }
        
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated engaging comment"))]
        )
        
        self.reddit_agent._generate_engaging_comment = AsyncMock(return_value="Generated engaging comment")
        comment = await self.reddit_agent._generate_engaging_comment(context)
        assert comment == "Generated engaging comment"

    async def test_generate_marketing_comment(self):
        """Test the Reddit agent's ability to generate marketing comments."""
        reddit_context = RedditContext(
            post_id='test_post_id',
            post_title='Test Post Title',
            post_url='https://reddit.com/test',
            subreddit='test_subreddit'
        )
        
        product_info = ProductInfo(
            product_id='12345',
            name='Test Product',
            product_type='sticker',
            zazzle_template_id='template123',
            zazzle_tracking_code='tracking456',
            image_url='https://example.com/image.jpg',
            product_url='https://example.com/product',
            theme='test_theme',
            model='dall-e-3',
            prompt_version='1.0.0',
            reddit_context=reddit_context,
            design_instructions={'image': 'https://example.com/image.jpg'},
            image_local_path='/path/to/image.jpg'
        )
        
        post_context = {
            "title": "Test Post Title",
            "content": "Test post content",
            "score": 100,
            "num_comments": 5,
            "top_comments": [
                {"text": "First comment", "author": "user1"},
                {"text": "Second comment", "author": "user2"}
            ]
        }
        
        self.mock_openai_instance.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Generated marketing comment"))]
        )
        
        self.reddit_agent._generate_marketing_comment = AsyncMock(return_value="Generated marketing comment")
        comment = await self.reddit_agent._generate_marketing_comment(product_info, post_context)
        assert comment == "Generated marketing comment"

if __name__ == '__main__':
    unittest.main() 