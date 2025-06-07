import pytest
from unittest.mock import Mock, patch, MagicMock
from app.clients.reddit_client import RedditClient
import os
import logging
import json

# Configure logging for tests
@pytest.fixture(autouse=True)
def setup_logging(caplog):
    caplog.set_level(logging.INFO)

@pytest.fixture
def mock_reddit():
    """Create a mock Reddit instance."""
    with patch('praw.Reddit') as mock:
        yield mock

@pytest.fixture
def reddit_client(mock_reddit, monkeypatch, request):
    """Create a RedditClient instance with mocked Reddit and configurable mode."""
    mode = request.param if hasattr(request, 'param') else 'dryrun' # Default to dryrun
    monkeypatch.setenv('REDDIT_MODE', mode)
    return RedditClient()

@pytest.fixture
def client(mock_reddit, monkeypatch):
    """Create a RedditClient instance with mocked Reddit for testing."""
    monkeypatch.setenv('REDDIT_MODE', 'dryrun')
    return RedditClient()

# Parametrize common actions for dryrun and live modes
@pytest.mark.parametrize('reddit_client', ['dryrun'], indirect=True)
class TestRedditClientDryRun:
    def test_upvote_post_dry_run(self, reddit_client, mock_reddit, caplog):
        """Test upvoting a post in dry run mode."""
        result = reddit_client.upvote_post('test_post_id')
        assert result['action'] == 'would upvote'
        log_entry = next((json.loads(r.getMessage()) for r in caplog.records if r.levelname == 'INFO' and 'operation' in json.loads(r.getMessage()) and json.loads(r.getMessage())['operation'] == 'upvote_post' and 'details' in json.loads(r.getMessage())), None)
        assert log_entry is not None
        assert log_entry['details']['post_id'] == 'test_post_id'

    def test_downvote_post_dry_run(self, reddit_client, mock_reddit, caplog):
        """Test downvoting a post in dry run mode."""
        result = reddit_client.downvote_post('test_post_id')
        assert result['action'] == 'would downvote'
        log_entry = next((json.loads(r.getMessage()) for r in caplog.records if r.levelname == 'INFO' and 'operation' in json.loads(r.getMessage()) and json.loads(r.getMessage())['operation'] == 'downvote_post' and 'details' in json.loads(r.getMessage())), None)
        assert log_entry is not None
        assert log_entry['details']['post_id'] == 'test_post_id'

    def test_upvote_comment_dry_run(self, reddit_client, mock_reddit, caplog):
        """Test upvoting a comment in dry run mode."""
        result = reddit_client.upvote_comment('test_comment_id')
        assert result['action'] == 'would upvote'
        log_entry = next((json.loads(r.getMessage()) for r in caplog.records if r.levelname == 'INFO' and 'operation' in json.loads(r.getMessage()) and json.loads(r.getMessage())['operation'] == 'upvote_comment' and 'details' in json.loads(r.getMessage())), None)
        assert log_entry is not None
        assert log_entry['details']['comment_id'] == 'test_comment_id'

    def test_downvote_comment_dry_run(self, reddit_client, mock_reddit, caplog):
        """Test downvoting a comment in dry run mode."""
        result = reddit_client.downvote_comment('test_comment_id')
        assert result['action'] == 'would downvote'
        log_entry = next((json.loads(r.getMessage()) for r in caplog.records if r.levelname == 'INFO' and 'operation' in json.loads(r.getMessage()) and json.loads(r.getMessage())['operation'] == 'downvote_comment' and 'details' in json.loads(r.getMessage())), None)
        assert log_entry is not None
        assert log_entry['details']['comment_id'] == 'test_comment_id'

    def test_comment_on_post_dry_run(self, reddit_client, mock_reddit, caplog):
        """Test commenting on a post in dry run mode."""
        result = reddit_client.comment_on_post('test_post_id', 'test comment')
        assert result['action'] == 'would comment on post'
        log_entry = next((json.loads(r.getMessage()) for r in caplog.records if r.levelname == 'INFO' and 'operation' in json.loads(r.getMessage()) and json.loads(r.getMessage())['operation'] == 'comment_on_post' and 'details' in json.loads(r.getMessage())), None)
        assert log_entry is not None
        assert log_entry['details']['post_id'] == 'test_post_id'
        assert log_entry['details']['comment_length'] == len('test comment')

    def test_reply_to_comment_dry_run(self, reddit_client, mock_reddit, caplog):
        """Test replying to a comment in dry run mode."""
        result = reddit_client.reply_to_comment('test_comment_id', 'test reply')
        assert result['action'] == 'would reply to comment'
        log_entry = next((json.loads(r.getMessage()) for r in caplog.records if r.levelname == 'INFO' and 'operation' in json.loads(r.getMessage()) and json.loads(r.getMessage())['operation'] == 'reply_to_comment' and 'details' in json.loads(r.getMessage())), None)
        assert log_entry is not None
        assert log_entry['details']['comment_id'] == 'test_comment_id'

    def test_post_content_dry_run(self, reddit_client, mock_reddit, caplog):
        """Test posting content in dry run mode."""
        result = reddit_client.post_content('test_subreddit', 'test title', 'test content')
        assert result['action'] == 'would post content'
        log_entry = next((json.loads(r.getMessage()) for r in caplog.records if r.levelname == 'INFO' and 'operation' in json.loads(r.getMessage()) and json.loads(r.getMessage())['operation'] == 'post_content' and 'details' in json.loads(r.getMessage())), None)
        assert log_entry is not None
        assert log_entry['details']['subreddit'] == 'test_subreddit'
        assert log_entry['details']['title_length'] == len('test title')
        assert log_entry['details']['content_length'] == len('test content')

@pytest.fixture
def reddit_client_dryrun():
    """Create a RedditClient instance in dryrun mode."""
    os.environ['REDDIT_MODE'] = 'dryrun'
    return RedditClient()

class TestRedditClientCommon:
    def test_initialization_default_dry_run(self, mock_reddit, caplog):
        """Test RedditClient initialization defaults to dry run and logs it."""
        client = RedditClient()
        assert client.mode == 'dryrun'
        log_entry = next((json.loads(r.getMessage()) for r in caplog.records if r.levelname == 'INFO' and 'operation' in json.loads(r.getMessage()) and json.loads(r.getMessage())['operation'] == 'init' and 'details' in json.loads(r.getMessage()) and json.loads(r.getMessage())['details'].get('message') == "Operating in DRY RUN mode. No actual Reddit actions will be performed."), None)
        assert log_entry is not None
        assert log_entry['details']['mode'] == 'dryrun' # Corrected assertion path

    def test_initialization_live_mode(self, mock_reddit, monkeypatch, caplog):
        """Test RedditClient initialization in live mode and logs it."""
        monkeypatch.setenv('REDDIT_MODE', 'live')
        client = RedditClient()
        assert client.mode == 'live'
        log_entry = next((json.loads(r.getMessage()) for r in caplog.records if r.levelname == 'INFO' and 'operation' in json.loads(r.getMessage()) and json.loads(r.getMessage())['operation'] == 'init' and 'details' in json.loads(r.getMessage()) and json.loads(r.getMessage())['details'].get('message') == "Operating in LIVE mode. Actions will be performed on Reddit."), None)
        assert log_entry is not None
        assert log_entry['details']['mode'] == 'live' # Corrected assertion path

    def test_initialization_invalid_mode_defaults_to_dryrun(self, mock_reddit, monkeypatch, caplog):
        """Test RedditClient initialization with invalid mode defaults to dry run and warns."""
        monkeypatch.setenv('REDDIT_MODE', 'invalid_mode')
        client = RedditClient()
        assert client.mode == 'dryrun'
        warning_log_entry = next((json.loads(r.getMessage()) for r in caplog.records if r.levelname == 'INFO' and 'operation' in json.loads(r.getMessage()) and json.loads(r.getMessage())['operation'] == 'init' and 'details' in json.loads(r.getMessage()) and json.loads(r.getMessage())['details'].get('message') and "Invalid REDDIT_MODE" in json.loads(r.getMessage())['details'].get('message')), None)
        assert warning_log_entry is not None
        assert warning_log_entry['details']['mode'] == 'invalid_mode' # Corrected assertion path
        dryrun_log_entry = next((json.loads(r.getMessage()) for r in caplog.records if r.levelname == 'INFO' and 'operation' in json.loads(r.getMessage()) and json.loads(r.getMessage())['operation'] == 'init' and 'details' in json.loads(r.getMessage()) and json.loads(r.getMessage())['details'].get('message') == "Operating in DRY RUN mode. No actual Reddit actions will be performed."), None)
        assert dryrun_log_entry is not None
        assert dryrun_log_entry['details']['mode'] == 'dryrun' # Corrected assertion path

    def test_get_subreddit(self, reddit_client, mock_reddit):
        """Test getting a subreddit."""
        mock_subreddit = MagicMock()
        mock_reddit.return_value.subreddit.return_value = mock_subreddit
        subreddit = reddit_client.get_subreddit('test_subreddit')
        assert subreddit == mock_subreddit
        mock_reddit.return_value.subreddit.assert_called_once_with('test_subreddit')

    def test_get_post(self, reddit_client, mock_reddit):
        """Test getting a post."""
        mock_submission = MagicMock()
        mock_reddit.return_value.submission.return_value = mock_submission
        post = reddit_client.get_post('test_post_id')
        assert post == mock_submission
        mock_reddit.return_value.submission.assert_called_once_with('test_post_id')

    def test_get_comment(self, reddit_client, mock_reddit):
        """Test getting a comment."""
        mock_comment = MagicMock()
        mock_reddit.return_value.comment.return_value = mock_comment
        comment = reddit_client.get_comment('test_comment_id')
        assert comment == mock_comment
        mock_reddit.return_value.comment.assert_called_once_with('test_comment_id')

    def test_get_post_context(self, reddit_client, mock_reddit):
        """Test getting post context."""
        # In dry run mode, we expect simulated data
        if reddit_client.mode == 'dryrun':
            result = reddit_client.get_post_context('test_post_id')
            assert 'post_id' in result
            assert 'title' in result
            assert 'content' in result
            assert 'top_comments' in result
            assert len(result['top_comments']) == 1
            assert result['top_comments'][0]['id'] == 'dryrun_comment_id'
        else:
            # Live mode assertions (simplified, actual mock setup would be more complex)
            mock_submission = MagicMock()
            mock_reddit.return_value.submission.return_value = mock_submission
            mock_comment = MagicMock()
            mock_submission.comments.list.return_value = [mock_comment]
            result = reddit_client.get_post_context('test_post_id')
            assert result['post_id'] == mock_submission.id
            assert result['title'] == mock_submission.title
            assert result['content'] == mock_submission.selftext
            assert result['top_comments'][0]['id'] == mock_comment.id

    def test_get_comment_context(self, reddit_client, mock_reddit):
        """Test getting comment context."""
        if reddit_client.mode == 'dryrun':
            result = reddit_client.get_comment_context('test_comment_id')
            assert 'comment_id' in result
            assert 'body' in result
            assert 'post_id' in result
        else:
            mock_comment = MagicMock()
            mock_reddit.return_value.comment.return_value = mock_comment
            result = reddit_client.get_comment_context('test_comment_id')
            assert result['comment_id'] == mock_comment.id
            assert result['body'] == mock_comment.body
            assert result['post_id'] == mock_comment.submission.id

    def test_get_trending_posts(self, reddit_client, mock_reddit):
        """Test getting trending posts."""
        if reddit_client.mode == 'dryrun':
            result = reddit_client.get_trending_posts('test_subreddit', limit=1)
            assert len(result) == 1
            assert result[0]['id'] == 'dryrun_post_0'
            assert 'title' in result[0]
            assert 'url' in result[0]
        else:
            mock_subreddit = MagicMock()
            mock_reddit.return_value.subreddit.return_value = mock_subreddit
            mock_submission = MagicMock()
            mock_subreddit.hot.return_value = [mock_submission]
            result = reddit_client.get_trending_posts('test_subreddit')
            assert result == [
                {
                    'id': mock_submission.id,
                    'title': mock_submission.title,
                    'url': mock_submission.url,
                    'score': mock_submission.score,
                    'num_comments': mock_submission.num_comments,
                    'created_utc': mock_submission.created_utc
                }
            ]

    def test_post_product(self, reddit_client_dryrun):
        """Test posting a product."""
        product_id = "test_product_id"
        product_name = "Test Product Name"
        content = "Test product content."
        result = reddit_client_dryrun.post_product(product_id, product_name, content)
        assert result['action'] == 'would post content'
        assert result['product_id'] == product_id
        assert result['product_name'] == product_name
        assert result['subreddit'] == "test_subreddit" # Hardcoded in client
        assert result['title'] == product_name
        assert result['content'] == content

if __name__ == '__main__':
    pytest.main() 