import unittest
from unittest.mock import patch, MagicMock
import os
from app.agents.reddit_agent import RedditAgent
from app.product_designer import ZazzleProductDesigner
import logging
from io import StringIO
import praw
from app.models import Product, ContentType
import pytest
from unittest.mock import Mock

class TestRedditAgent(unittest.TestCase):
    """Test cases for the Reddit Agent."""

    def setUp(self):
        """Set up the test environment."""
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

        self.reddit_agent = RedditAgent(subreddit_name='test_subreddit')
        self.log_capture = StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        logging.getLogger('app').addHandler(self.handler)
        self.addCleanup(lambda: logging.getLogger('app').removeHandler(self.handler))

    @patch('app.product_designer.ZazzleProductDesigner.create_product')
    def test_get_product_info(self, mock_create_product):
        """Test retrieving product information from the Zazzle Product Designer."""
        mock_create_product.return_value = {'product_id': '12345', 'product_url': 'https://example.com/product'}
        design_instructions = {'text': 'Custom Golf Ball', 'color': 'Red', 'quantity': 12}
        result = self.reddit_agent.get_product_info(design_instructions)
        self.assertEqual(result, {'product_id': '12345', 'product_url': 'https://example.com/product'})
        mock_create_product.assert_called_once_with(design_instructions)

    def test_interact_with_votes(self):
        """Test upvoting and downvoting on a dummy post."""
        mock_submission = MagicMock()
        mock_submission.id = "dummy_id"
        mock_submission.title = "Dummy Post Title"
        mock_submission.upvote = MagicMock()
        mock_submission.downvote = MagicMock()
        # Patch reddit_agent.reddit.submission to return our mock_submission
        self.reddit_agent.reddit.submission = MagicMock(return_value=mock_submission)
        # Call the method with a post id
        self.reddit_agent.interact_with_votes("dummy_id")
        mock_submission.upvote.assert_called_once()
        mock_submission.downvote.assert_called_once()

    @patch.object(ZazzleProductDesigner, 'create_product')
    def test_find_and_create_product(self, mock_create_product):
        mock_reddit = MagicMock()
        mock_subreddit_instance = MagicMock()
        mock_post = MagicMock()
        mock_post.title = "Golf Joke"
        mock_post.selftext = "This is a funny golf joke."
        mock_post.id = "joke_post_id"
        mock_post.permalink = "/r/golf/comments/joke_post_id/golf_joke/"
        mock_post.created_utc = 1678886400.0
        mock_comment1 = MagicMock()
        mock_comment1.body = "Haha, that's a great one!"
        mock_comment1.id = "comment1_id"
        mock_comment1.score = 10
        mock_comment2 = MagicMock()
        mock_comment2.body = "Classic golf humor."
        mock_comment2.id = "comment2_id"
        mock_comment2.score = 5
        mock_post.comments.list.return_value = [mock_comment1, mock_comment2]
        mock_post.comments.replace_more = MagicMock()
        mock_subreddit_instance.hot.return_value = iter([mock_post])
        mock_reddit.subreddit.return_value = mock_subreddit_instance
        mock_create_product.return_value = {
            'product_url': 'http://zazzle.com/custom_sticker_url',
            'text': 'Golf Joke',
            'image_url': 'http://example.com/image.png',
            'theme': 'jokes'
        }
        self.reddit_agent.reddit = mock_reddit  # Set the reddit attribute directly
        result = self.reddit_agent.find_and_create_product()
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], 'Golf Joke')
        self.assertEqual(result['reddit_context']['title'], mock_post.title)
        self.assertEqual(result['reddit_context']['url'], f'https://reddit.com{mock_post.permalink}')
        self.assertEqual(result['reddit_context']['theme'], 'jokes')
        self.assertIn('product_url', result)
        mock_create_product.assert_called_once()
        call_args, call_kwargs = mock_create_product.call_args
        self.assertIn('text', call_args[0])
        self.assertEqual(call_args[0]['text'], 'Golf Joke')
        self.assertIn('image_iid', call_args[0])

    @patch.object(RedditAgent, 'interact_with_votes')
    @patch.object(RedditAgent, 'get_product_info')
    def test_interact_with_subreddit(self, mock_get_product_info, mock_interact_with_votes):
        # Provide a product_info with required fields
        product_info = {'product_id': 'dummy_prod_id', 'product_url': 'http://dummy.link/product'}
        # Patch reddit_agent.reddit.subreddit().submit to a mock to avoid real API calls
        mock_subreddit = MagicMock()
        mock_subreddit.submit = MagicMock()
        self.reddit_agent.reddit.subreddit = MagicMock(return_value=mock_subreddit)
        # Call the method and assert no exceptions
        try:
            self.reddit_agent.interact_with_subreddit(product_info)
        except Exception as e:
            self.fail(f"interact_with_subreddit raised an exception: {e}")

@pytest.fixture
def reddit_agent():
    return RedditAgent()

@pytest.fixture
def mock_comment():
    comment = Mock()
    comment.id = "test_comment_id"
    comment.body = "Test comment body"
    comment.author = "test_user"
    comment.subreddit.display_name = "test_subreddit"
    comment.upvote = Mock()
    comment.downvote = Mock()
    comment.stickied = False
    return comment

@pytest.fixture
def mock_submission(mock_comment):
    submission = Mock()
    submission.id = "test_post_id"
    submission.title = "Test Post Title"
    submission.subreddit.display_name = "test_subreddit"
    comments_mock = Mock()
    comments_mock.replace_more = Mock()
    comments_mock.list = Mock(return_value=iter([mock_comment]))
    submission.comments = comments_mock
    return submission

def test_interact_with_comment_votes(mock_comment, mock_submission):
    """Test the Reddit agent's ability to upvote and downvote comments."""
    with patch('praw.Reddit') as mock_reddit:
        mock_reddit_instance = Mock()
        mock_reddit.return_value = mock_reddit_instance
        mock_reddit_instance.comment.return_value = mock_comment
        reddit_agent = RedditAgent()
        result = reddit_agent.interact_with_votes(mock_submission.id, mock_comment.id)
        assert result is not None
        assert result['type'] == 'comment'
        assert result['post_id'] == mock_submission.id
        assert result['comment_id'] == mock_comment.id
        assert result['comment_text'] == mock_comment.body
        assert 'comment_link' in result
        mock_comment.upvote.assert_called_once()
        mock_comment.downvote.assert_called_once()

def test_interact_with_users_comments(mock_comment, mock_submission):
    """Test the Reddit agent's ability to interact with comments in a post."""
    with patch('praw.Reddit') as mock_reddit:
        mock_reddit_instance = Mock()
        mock_reddit.return_value = mock_reddit_instance
        mock_subreddit = Mock()
        mock_subreddit.hot.return_value = iter([mock_submission])
        mock_reddit_instance.subreddit.return_value = mock_subreddit
        mock_reddit_instance.comment.return_value = mock_comment
        reddit_agent = RedditAgent()
        reddit_agent.interact_with_users("test_product_id")
        mock_submission.comments.replace_more.assert_called_once_with(limit=0)
        mock_submission.comments.list.assert_called_once()

if __name__ == '__main__':
    unittest.main() 