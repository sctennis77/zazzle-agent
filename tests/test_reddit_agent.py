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
            'theme': 'golf humor'
        }
        self.reddit_agent.reddit = mock_reddit  # Set the reddit attribute directly
        result = self.reddit_agent.find_and_create_product()
        self.assertIsNotNone(result)
        self.assertEqual(result['text'], 'Golf Joke')
        self.assertEqual(result['reddit_context']['title'], mock_post.title)
        self.assertEqual(result['reddit_context']['url'], f'https://reddit.com{mock_post.permalink}')
        self.assertIn('theme', result['reddit_context'])
        self.assertIsInstance(result['reddit_context']['theme'], str)
        self.assertIn('product_url', result)
        mock_create_product.assert_called_once()
        call_args, call_kwargs = mock_create_product.call_args
        self.assertIn('text', call_args[0])
        self.assertIn('image', call_args[0])
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

def test_comment_on_post(mock_submission):
    """Test the Reddit agent's ability to comment on posts."""
    with patch('praw.Reddit') as mock_reddit:
        mock_reddit_instance = Mock()
        mock_reddit.return_value = mock_reddit_instance
        mock_reddit_instance.submission.return_value = mock_submission
        
        reddit_agent = RedditAgent()
        test_comment = "Test comment text"
        result = reddit_agent.comment_on_post(mock_submission.id, test_comment)
        
        assert result is not None
        assert result['type'] == 'post_comment'
        assert result['post_id'] == mock_submission.id
        assert result['post_title'] == mock_submission.title
        assert 'post_link' in result
        assert result['comment_text'] == test_comment
        assert result['action'] == 'Would reply to post with comment'

def test_comment_on_post_default_text(mock_submission):
    """Test the Reddit agent's ability to comment on posts with default text."""
    with patch('praw.Reddit') as mock_reddit:
        mock_reddit_instance = Mock()
        mock_reddit.return_value = mock_reddit_instance
        mock_reddit_instance.submission.return_value = mock_submission
        
        reddit_agent = RedditAgent()
        result = reddit_agent.comment_on_post(mock_submission.id)
        
        assert result is not None
        assert result['type'] == 'post_comment'
        assert result['post_id'] == mock_submission.id
        assert result['post_title'] == mock_submission.title
        assert 'post_link' in result
        assert result['comment_text'] == "Thanks for sharing this interesting post! I appreciate the insights."
        assert result['action'] == 'Would reply to post with comment'

def test_engage_with_post():
    """Test the Reddit agent's ability to engage with posts by generating context-aware comments."""
    # Create a mock post
    mock_post = MagicMock()
    mock_post.id = "test123"
    mock_post.title = "Test Post Title"
    mock_post.selftext = "Test post content"
    mock_post.score = 100
    mock_post.num_comments = 5
    
    # Create mock comments
    mock_comment1 = MagicMock()
    mock_comment1.body = "First comment"
    mock_comment1.author = "user1"
    mock_comment1.score = 50
    
    mock_comment2 = MagicMock()
    mock_comment2.body = "Second comment"
    mock_comment2.author = "user2"
    mock_comment2.score = 30
    
    # Create a mock comment list with replace_more method
    mock_comments = MagicMock()
    mock_comments.replace_more.return_value = [mock_comment1, mock_comment2]
    mock_comments.list.return_value = [mock_comment1, mock_comment2] # Ensure .list() returns comments
    mock_post.comments = mock_comments
    mock_post.permalink = f"/r/golf/comments/{mock_post.id}/"
    mock_post.subreddit.display_name = "golf"

    # Set stickied to False for mocked comments
    mock_comment1.stickied = False
    mock_comment2.stickied = False

    # Create a mock Reddit instance
    mock_reddit = MagicMock()
    mock_reddit.submission.return_value = mock_post

    # Create the agent with the mock
    agent = RedditAgent()
    agent.reddit = mock_reddit
    
    # Test engaging with the post
    result = agent.engage_with_post("test123")
    
    # Verify the result
    assert result is not None
    assert result["type"] == "post_engagement"
    assert result["post_id"] == "test123"
    assert result["post_title"] == "Test Post Title"
    assert result["post_link"] == f"https://reddit.com/r/{mock_post.subreddit.display_name}/comments/{mock_post.id}"
    assert "comment_text" in result
    assert result["action"] == "Would engage with post using generated comment"
    
    # Verify post context
    assert "post_context" in result
    context = result["post_context"]
    assert context["title"] == "Test Post Title"
    assert context["text"] == "Test post content"
    assert context["score"] == 100
    assert context["num_comments"] == 5
    assert len(context["top_comments"]) == 2
    assert context["top_comments"][0]["text"] == "First comment"
    assert context["top_comments"][0]["author"] == "user1"
    assert context["top_comments"][1]["text"] == "Second comment"
    assert context["top_comments"][1]["author"] == "user2"

def test_analyze_post_context():
    """Test the Reddit agent's ability to analyze post context."""
    # Create a mock post
    mock_post = MagicMock()
    mock_post.title = "Test Post Title"
    mock_post.selftext = "Test post content"
    mock_post.score = 100
    mock_post.num_comments = 5
    
    # Create mock comments
    mock_comment1 = MagicMock()
    mock_comment1.body = "First comment"
    mock_comment1.author = "user1"
    mock_comment1.score = 50
    
    mock_comment2 = MagicMock()
    mock_comment2.body = "Second comment"
    mock_comment2.author = "user2"
    mock_comment2.score = 30
    
    # Set stickied to False for mocked comments
    mock_comment1.stickied = False
    mock_comment2.stickied = False

    # Create a mock comment list with replace_more method
    mock_comments = MagicMock()
    mock_comments.replace_more.return_value = [] # This line is important, as replace_more modifies in place
    mock_comments.list.return_value = [mock_comment1, mock_comment2] # Ensure .list() returns comments
    mock_post.comments = mock_comments
    mock_post.subreddit.display_name = "golf"
    
    # Create the agent
    agent = RedditAgent()
    
    # Test analyzing post context
    context = agent._analyze_post_context(mock_post)
    
    # Verify the context
    assert context["title"] == "Test Post Title"
    assert context["text"] == "Test post content"
    assert context["score"] == 100
    assert context["num_comments"] == 5
    assert len(context["top_comments"]) == 2
    assert context["top_comments"][0]["text"] == "First comment"
    assert context["top_comments"][0]["author"] == "user1"
    assert context["top_comments"][1]["text"] == "Second comment"
    assert context["top_comments"][1]["author"] == "user2"

def test_generate_engaging_comment():
    """Test the Reddit agent's ability to generate engaging comments."""
    # Create test context
    context = {
        "title": "Test Post Title",
        "text": "Test post content",
        "score": 100,
        "num_comments": 5,
        "top_comments": [
            {"text": "First comment", "author": "user1"},
            {"text": "Second comment", "author": "user2"}
        ]
    }

    # Mock the OpenAI API call
    with patch('openai.OpenAI') as mock_openai_client:
        mock_instance = MagicMock()
        mock_openai_client.return_value = mock_instance
        
        mock_choice = MagicMock()
        mock_choice.message.content = "Generated engaging comment"
        mock_instance.chat.completions.create.return_value.choices = [mock_choice]

        # Create the agent within the patch context
        agent = RedditAgent()

        # Test generating a comment
        comment = agent._generate_engaging_comment(context)

        # Verify the comment
        assert isinstance(comment, str)
        assert len(comment) > 0
        assert len(comment) <= 280  # Reddit comment length limit
        assert comment == "Generated engaging comment"

def test_generate_marketing_comment():
    """Test the Reddit agent's ability to generate marketing comments."""
    # Create a dummy product
    product = Product(
        product_id="test_product_id",
        name="Custom Golf Ball",
        content="A high-quality custom golf ball for enthusiasts. Get your personalized golf balls today!",
        affiliate_link="https://www.zazzle.com/custom_golf_ball_link"
    )
    
    # Create test post context
    post_context = {
        "title": "Discussion on best golf equipment",
        "text": "Looking for recommendations on durable golf balls.",
        "score": 50,
        "num_comments": 10,
        "top_comments": [
            {"text": "I prefer Titleist Pro V1.", "author": "golfer1"},
            {"text": "Check out Bridgestone B XS.", "author": "golfer2"}
        ]
    }
    
    # Mock the OpenAI API call
    with patch('openai.OpenAI') as mock_openai_client:
        mock_instance = MagicMock()
        mock_openai_client.return_value = mock_instance
        
        mock_choice = MagicMock()
        mock_choice.message.content = "This golf ball is perfect for you: https://www.zazzle.com/custom_golf_ball_link"
        mock_instance.chat.completions.create.return_value.choices = [mock_choice]

        # Create the agent within the patch context
        agent = RedditAgent()
        
        # Test generating a marketing comment
        comment = agent._generate_marketing_comment(product, post_context)
        
        # Verify the comment
        assert isinstance(comment, str)
        assert len(comment) > 0
        assert "https://www.zazzle.com/custom_golf_ball_link" in comment
        assert comment == "This golf ball is perfect for you: https://www.zazzle.com/custom_golf_ball_link"

def test_engage_with_post_marketing():
    """Test the Reddit agent's ability to engage with posts with marketing comments."""
    # Create a mock post
    mock_post = MagicMock()
    mock_post.id = "test456"
    mock_post.title = "Need new golf balls for the season"
    mock_post.selftext = "Any recommendations for durable and long-lasting golf balls?"
    mock_post.score = 70
    mock_post.num_comments = 15
    mock_post.permalink = f"/r/golf/comments/{mock_post.id}/"
    mock_post.subreddit.display_name = "golf"

    # Create mock comments
    mock_comment1 = MagicMock()
    mock_comment1.body = "Try Titleist Pro V1, they are great!"
    mock_comment1.author = "userA"
    mock_comment1.score = 25
    mock_comment1.stickied = False

    mock_comment2 = MagicMock()
    mock_comment2.body = "Bridgestone B XS are also good for distance."
    mock_comment2.author = "userB"
    mock_comment2.score = 15
    mock_comment2.stickied = False

    # Create a mock comment list with replace_more method
    mock_comments = MagicMock()
    mock_comments.replace_more.return_value = []
    mock_comments.list.return_value = [mock_comment1, mock_comment2]
    mock_post.comments = mock_comments

    # Mock Reddit and ProductDesigner
    mock_reddit = MagicMock()
    mock_reddit.submission.return_value = mock_post
    
    mock_product_designer = MagicMock()
    mock_product_designer.create_product.return_value = {
        'product_url': "https://www.zazzle.com/generated_product_link"
    }

    # Mock the _determine_product_idea to return a valid product idea
    with patch.object(RedditAgent, '_determine_product_idea', return_value={
        'text': 'Golf Balls',
        'color': 'White',
        'quantity': 12,
        'theme': 'equipment'
    }):
        with patch('openai.OpenAI') as mock_openai_client:
            mock_instance = MagicMock()
            mock_openai_client.return_value = mock_instance
            mock_choice = MagicMock()
            mock_choice.message.content = "Check out this cool product!"
            mock_instance.chat.completions.create.return_value.choices = [mock_choice]

            agent = RedditAgent()
            agent.reddit = mock_reddit
            agent.product_designer = mock_product_designer

            result = agent.engage_with_post_marketing("test456")

            assert result is not None
            assert result["type"] == "post_marketing_comment"
            assert result["post_id"] == "test456"
            assert result["post_title"] == "Need new golf balls for the season"
            assert result["post_link"] == f"https://reddit.com/r/{mock_post.subreddit.display_name}/comments/{mock_post.id}"
            assert "product_info" in result
            assert result["comment_text"] == "Check out this cool product!"
            assert result["action"] == "Would reply to post with marketing comment"

def test_reply_to_comment_with_marketing():
    """Test the Reddit agent's ability to reply to a comment with a marketing message."""
    # Create a mock comment
    mock_comment = MagicMock()
    mock_comment.id = "test_comment_id"
    mock_comment.body = "This is a great discussion about golf equipment!"
    mock_comment.submission.id = "test_post_id"
    mock_comment.submission.title = "Best Golf Equipment"
    mock_comment.submission.selftext = "Looking for recommendations on golf equipment."
    mock_comment.subreddit.display_name = "golf"

    # Create a dummy product
    product = Product(
        product_id="test_product_123",
        name="Custom Golf Driver",
        content="Improve your swing with our new custom golf driver!",
        affiliate_link="https://www.zazzle.com/custom_golf_driver_link"
    )

    # Create test post context
    post_context = {
        "title": "Best Golf Equipment",
        "text": "Looking for recommendations on golf equipment.",
        "score": 100,
        "num_comments": 5,
        "top_comments": [
            {"text": "What about a new driver?", "author": "golferX"}
        ]
    }

    # Mock the Reddit API and OpenAI API
    mock_reddit = MagicMock()
    mock_reddit.comment.return_value = mock_comment

    with patch('openai.OpenAI') as mock_openai_client:
        mock_instance = MagicMock()
        mock_openai_client.return_value = mock_instance
        mock_choice = MagicMock()
        mock_choice.message.content = "That's a great point! If you're looking for a new driver, check out our custom options: https://www.zazzle.com/custom_golf_driver_link"
        mock_instance.chat.completions.create.return_value.choices = [mock_choice]

        agent = RedditAgent()
        agent.reddit = mock_reddit

        result = agent.reply_to_comment_with_marketing(mock_comment.id, product, post_context)

        assert result is not None
        assert result["type"] == "comment_marketing_reply"
        assert result["comment_id"] == "test_comment_id"
        assert result["comment_text"] == "This is a great discussion about golf equipment!"
        assert result["post_id"] == "test_post_id"
        assert result["post_title"] == "Best Golf Equipment"
        assert result["post_link"] == f"https://reddit.com/r/{mock_comment.subreddit.display_name}/comments/{mock_comment.submission.id}/_/{mock_comment.id}"
        assert result["product_info"]["name"] == "Custom Golf Driver"
        assert result["product_info"]["affiliate_link"] == "https://www.zazzle.com/custom_golf_driver_link"
        assert result["reply_text"] == "That's a great point! If you're looking for a new driver, check out our custom options: https://www.zazzle.com/custom_golf_driver_link"
        assert result["action"] == "Would reply to comment with marketing content"

if __name__ == '__main__':
    unittest.main() 