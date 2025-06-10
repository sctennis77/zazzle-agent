import os
import pytest
import json
import csv
from unittest.mock import patch, mock_open, MagicMock, AsyncMock, Mock
from app.main import ensure_output_dir, save_to_csv, run_full_pipeline, main, log_product_info
from app.models import ProductInfo, RedditContext, ProductIdea, PipelineConfig
from app.agents.reddit_agent import RedditAgent
from app.content_generator import ContentGenerator
from app.affiliate_linker import ZazzleAffiliateLinker

@pytest.fixture
def mock_product_info():
    reddit_context = RedditContext(
        post_id="test_post_id",
        post_title="Test Post",
        post_url="https://reddit.com/r/test/comments/test_post_id",
        subreddit="test",
        post_content="Test content"
    )
    return ProductInfo(
        product_id="test_product_id",
        name="Test Product",
        product_type="sticker",
        zazzle_template_id="test_template_id",
        zazzle_tracking_code="test_tracking_code",
        image_url="https://example.com/test.jpg",
        product_url="https://zazzle.com/test_product",
        theme="test theme",
        model="test_model",
        prompt_version="1.0.0",
        reddit_context=reddit_context,
        design_instructions={
            'content': 'Test content',
            'image': 'https://example.com/test.jpg'
        },
        image_local_path="/tmp/test.jpg"
    )

def test_ensure_output_dir_creates_directory(tmp_path):
    output_dir = tmp_path / "output"
    ensure_output_dir(str(output_dir))
    assert output_dir.exists()
    assert output_dir.is_dir()

def test_save_to_csv_success(mock_product_info, tmp_path):
    output_file = tmp_path / "test_output.csv"
    mock_writer = MagicMock()
    mock_writer.writeheader = MagicMock()
    mock_writer.writerows = MagicMock()
    
    with patch('builtins.open', mock_open()) as m:
        with patch('csv.DictWriter', return_value=mock_writer):
            save_to_csv([mock_product_info], str(output_file))
    
    m.assert_called_once_with(str(output_file), 'w', newline='')
    mock_writer.writeheader.assert_called_once()
    mock_writer.writerows.assert_called_once()

@pytest.mark.asyncio
async def test_run_full_pipeline_success(mock_product_info):
    with patch('app.main.RedditAgent') as mock_reddit_agent_class, \
         patch('app.agents.reddit_agent.RedditAgent') as mock_reddit_agent_impl:
        mock_agent = AsyncMock(spec=RedditAgent)
        mock_agent.find_and_create_product.return_value = mock_product_info
        mock_agent.reddit = MagicMock()  # Add mock reddit client
        mock_reddit_agent_class.return_value = mock_agent
        mock_reddit_agent_impl.return_value = mock_agent

        with patch('app.main.save_to_csv') as mock_save:
            config = PipelineConfig(
                model="dall-e-3",
                zazzle_template_id="test_template_id",
                zazzle_tracking_code="test_tracking_code",
                prompt_version="1.0.0"
            )
            result = await run_full_pipeline(config)

            # Verify the result
            assert result == mock_product_info
            
            # Verify the mock was called
            mock_agent.find_and_create_product.assert_called_once()
            mock_save.assert_called_once_with(mock_product_info)

            # Verify RedditAgent was initialized with correct config
            mock_reddit_agent_class.assert_called_once_with(config_or_model=config.model)

@pytest.mark.asyncio
async def test_run_full_pipeline_no_product_generated():
    with patch('app.main.RedditAgent') as mock_reddit_agent_class, \
         patch('app.agents.reddit_agent.RedditAgent') as mock_reddit_agent_impl:
        mock_agent = AsyncMock(spec=RedditAgent)
        mock_agent.find_and_create_product.return_value = None
        mock_agent.reddit = MagicMock()  # Add mock reddit client
        mock_reddit_agent_class.return_value = mock_agent
        mock_reddit_agent_impl.return_value = mock_agent

        with patch('app.main.save_to_csv') as mock_save:
            config = PipelineConfig(
                model="dall-e-3",
                zazzle_template_id="test_template_id",
                zazzle_tracking_code="test_tracking_code",
                prompt_version="1.0.0"
            )
            result = await run_full_pipeline(config)

            # Verify the result is None
            assert result is None
            
            # Verify the mock was called
            mock_agent.find_and_create_product.assert_called_once()
            mock_save.assert_not_called()

            # Verify RedditAgent was initialized with correct config
            mock_reddit_agent_class.assert_called_once_with(config_or_model=config.model)

@pytest.mark.asyncio
async def test_run_full_pipeline_error_handling():
    with patch('app.main.RedditAgent') as mock_reddit_agent_class, \
         patch('app.agents.reddit_agent.RedditAgent') as mock_reddit_agent_impl:
        mock_agent = AsyncMock(spec=RedditAgent)
        mock_agent.find_and_create_product.side_effect = Exception("Test error")
        mock_agent.reddit = MagicMock()  # Add mock reddit client
        mock_reddit_agent_class.return_value = mock_agent
        mock_reddit_agent_impl.return_value = mock_agent

        with patch('app.main.save_to_csv') as mock_save:
            config = PipelineConfig(
                model="dall-e-3",
                zazzle_template_id="test_template_id",
                zazzle_tracking_code="test_tracking_code",
                prompt_version="1.0.0"
            )
            
            # Verify that the error is raised
            with pytest.raises(Exception) as exc_info:
                await run_full_pipeline(config)
            
            assert str(exc_info.value) == "Test error"
            
            # Verify the mock was called
            mock_agent.find_and_create_product.assert_called_once()
            mock_save.assert_not_called()

            # Verify RedditAgent was initialized with correct config
            mock_reddit_agent_class.assert_called_once_with(config_or_model=config.model)

# Tests for main function argument parsing
@pytest.mark.asyncio
@patch('app.main.run_full_pipeline')
@patch('app.main.test_reddit_voting')
@patch('app.main.test_reddit_comment_voting')
@patch('app.main.test_reddit_post_comment')
@patch('app.main.test_reddit_engaging_comment')
@patch('app.main.test_reddit_marketing_comment')
@patch('app.main.test_reddit_comment_marketing_reply')
@patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(mode='full'))
async def test_main_full_mode(mock_parse_args, mock_reply, mock_marketing_comment, mock_engaging_comment, mock_post_comment, mock_comment_voting, mock_voting, mock_full_pipeline):
    await main()
    mock_full_pipeline.assert_called_once()
    mock_voting.assert_not_called()

@pytest.mark.asyncio
@patch('app.main.run_full_pipeline')
@patch('app.main.test_reddit_voting')
@patch('app.main.test_reddit_comment_voting')
@patch('app.main.test_reddit_post_comment')
@patch('app.main.test_reddit_engaging_comment')
@patch('app.main.test_reddit_marketing_comment')
@patch('app.main.test_reddit_comment_marketing_reply')
@patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(mode='test-vote'))
async def test_main_test_voting_mode(mock_parse_args, mock_reply, mock_marketing_comment, mock_engaging_comment, mock_post_comment, mock_comment_voting, mock_voting, mock_full_pipeline):
    await main()
    mock_voting.assert_called_once()
    mock_full_pipeline.assert_not_called()

@pytest.mark.asyncio
@patch('app.main.run_full_pipeline')
@patch('app.main.test_reddit_post_comment')
@patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(mode='test-comment'))
async def test_main_test_post_comment_mode(mock_parse_args, mock_post_comment, mock_full_pipeline):
    await main()
    mock_post_comment.assert_called_once()

@pytest.mark.asyncio
@patch('app.main.run_full_pipeline')
@patch('app.main.test_reddit_engaging_comment')
@patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(mode='test-engaging'))
async def test_main_test_engaging_comment_mode(mock_parse_args, mock_engaging_comment, mock_full_pipeline):
    await main()
    mock_engaging_comment.assert_called_once()

@pytest.mark.asyncio
@patch('app.main.run_full_pipeline')
@patch('app.main.test_reddit_marketing_comment')
@patch('argparse.ArgumentParser.parse_args', return_value=MagicMock(mode='test-marketing'))
async def test_main_test_marketing_comment_mode(mock_parse_args, mock_marketing_comment, mock_full_pipeline):
    await main()
    mock_marketing_comment.assert_called_once()

# New tests for test_reddit_voting function
@pytest.mark.asyncio
@patch('app.main.RedditAgent')
@patch('logging.Logger.info')
async def test_reddit_voting_found_post(mock_logger_info, MockRedditAgent):
    mock_agent_instance = MagicMock()
    MockRedditAgent.return_value = mock_agent_instance
    
    mock_subreddit = MagicMock()
    mock_agent_instance.reddit.subreddit.return_value = mock_subreddit
    
    mock_trending_post = MagicMock(id='post123', title='Test Post', permalink='/r/golf/comments/post123/test_post/')
    mock_subreddit.hot.return_value = iter([mock_trending_post])
    
    mock_agent_instance.interact_with_votes.return_value = {'type': 'vote', 'action': 'upvoted'}

    # Call the function directly
    from app.main import test_reddit_voting
    await test_reddit_voting()

    mock_agent_instance.reddit.subreddit.assert_called_once_with("golf")
    mock_subreddit.hot.assert_called_once_with(limit=1)
    mock_agent_instance.interact_with_votes.assert_called_once_with('post123')
    
    # Check logger calls
    log_msgs = [call.args[0] for call in mock_logger_info.call_args_list]
    assert any("Found trending post" in msg for msg in log_msgs)
    assert any(f"Title: {mock_trending_post.title}" in msg for msg in log_msgs)
    assert any(f"URL: https://reddit.com{mock_trending_post.permalink}" in msg for msg in log_msgs)
    assert any("Action taken" in msg for msg in log_msgs)

@pytest.mark.asyncio
@patch('app.main.RedditAgent')
@patch('logging.Logger.info')
async def test_reddit_voting_no_post_found(mock_logger_info, MockRedditAgent):
    mock_agent_instance = MagicMock()
    MockRedditAgent.return_value = mock_agent_instance
    
    mock_subreddit = MagicMock()
    mock_agent_instance.reddit.subreddit.return_value = mock_subreddit
    mock_subreddit.hot.return_value = iter([]) # Simulate no trending posts
    
    # Call the function directly
    from app.main import test_reddit_voting
    await test_reddit_voting()
    
    mock_agent_instance.reddit.subreddit.assert_called_once_with("golf")
    mock_subreddit.hot.assert_called_once_with(limit=1)
    mock_agent_instance.interact_with_votes.assert_not_called()
    log_msgs = [call.args[0] for call in mock_logger_info.call_args_list]
    assert any("No trending post found in r/golf." in msg for msg in log_msgs)

# New tests for test_reddit_comment_voting function
@pytest.mark.asyncio
@patch('app.main.RedditAgent')
@patch('logging.Logger.info')
async def test_reddit_comment_voting_found_post_and_comment(mock_logger_info, MockRedditAgent):
    mock_agent_instance = MagicMock()
    MockRedditAgent.return_value = mock_agent_instance
    
    mock_subreddit = MagicMock()
    mock_agent_instance.reddit.subreddit.return_value = mock_subreddit
    
    mock_trending_post = MagicMock(id='post123', title='Test Post', permalink='/r/golf/comments/post123/test_post/')
    
    mock_comment = MagicMock(id='comment123', body='Test Comment Body', author=MagicMock(name='testuser'), stickied=False)
    mock_trending_post.comments.replace_more.return_value = None # No more comments to load
    mock_trending_post.comments.list.return_value = [mock_comment]
    
    mock_subreddit.hot.return_value = iter([mock_trending_post])
    
    mock_agent_instance.interact_with_votes.return_value = {'type': 'comment_vote', 'action': 'upvoted'}

    # Call the function directly
    from app.main import test_reddit_comment_voting
    await test_reddit_comment_voting()

    mock_agent_instance.reddit.subreddit.assert_called_once_with("golf")
    mock_subreddit.hot.assert_called_once_with(limit=1)
    mock_trending_post.comments.replace_more.assert_called_once_with(limit=0)
    mock_trending_post.comments.list.assert_called_once()
    mock_agent_instance.interact_with_votes.assert_called_once_with('post123', 'comment123')
    
    log_msgs = [call.args[0] for call in mock_logger_info.call_args_list]
    assert any("Found trending post" in msg for msg in log_msgs)
    assert any(f"Title: {mock_trending_post.title}" in msg for msg in log_msgs)
    assert any(f"URL: https://reddit.com{mock_trending_post.permalink}" in msg for msg in log_msgs)
    assert any("Found comment" in msg for msg in log_msgs)
    assert any(f"Text: {mock_comment.body}" in msg for msg in log_msgs)
    assert any("Action taken" in msg for msg in log_msgs)

def test_save_to_csv():
    """Test saving product information to CSV with model and version."""
    # Test data
    reddit_context = RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit'
    )

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
        reddit_context=reddit_context,
        design_instructions={'image': 'https://example.com/image.jpg'},
        image_local_path='/path/to/image.jpg'
    )

    # Save to CSV
    test_file = 'test_products.csv'
    try:
        product_info.to_csv(test_file)

        # Verify CSV file exists and contains correct data
        assert os.path.exists(test_file)

        with open(test_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            row = rows[0]
            
            # Check required fields
            assert row['product_id'] == 'test_id'
            assert row['name'] == 'Test Product'
            assert row['product_type'] == 'sticker'
            assert row['zazzle_template_id'] == 'template123'
            assert row['zazzle_tracking_code'] == 'tracking456'
            assert row['image_url'] == 'https://example.com/image.jpg'
            assert row['product_url'] == 'https://example.com/product'
            assert row['theme'] == 'test_theme'
            assert row['model'] == 'dall-e-3'
            assert row['prompt_version'] == '1.0.0'
            assert row['image_local_path'] == '/path/to/image.jpg'

    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)

def test_save_to_csv_missing_fields():
    """Test saving product information to CSV with missing fields."""
    # Test data with missing fields
    reddit_context = RedditContext(
        post_id='test_post_id',
        post_title='Test Post Title',
        post_url='https://reddit.com/test',
        subreddit='test_subreddit'
    )

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
        reddit_context=reddit_context,
        design_instructions={'image': 'https://example.com/image.jpg'},
        image_local_path='/path/to/image.jpg'
    )

    # Save to CSV
    test_file = 'test_products.csv'
    try:
        product_info.to_csv(test_file)

        # Verify CSV file exists and contains correct data
        assert os.path.exists(test_file)

        with open(test_file, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            row = rows[0]
            
            # Check required fields
            assert row['product_id'] == 'test_id'
            assert row['name'] == 'Test Product'
            assert row['product_type'] == 'sticker'
            assert row['zazzle_template_id'] == 'template123'
            assert row['zazzle_tracking_code'] == 'tracking456'
            assert row['image_url'] == 'https://example.com/image.jpg'
            assert row['product_url'] == 'https://example.com/product'
            assert row['theme'] == 'test_theme'
            assert row['model'] == 'dall-e-3'
            assert row['prompt_version'] == '1.0.0'
            assert row['image_local_path'] == '/path/to/image.jpg'

    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file) 