import os
import pytest
import json
import csv
from unittest.mock import patch, mock_open, MagicMock, AsyncMock
from app.main import ensure_output_dir, save_to_csv, run_full_pipeline, main
from app.models import Product, ContentType

# Mock os.makedirs for ensure_output_dir
@patch('os.makedirs')
def test_ensure_output_dir_creates_directory(mock_makedirs):
    """Test that ensure_output_dir creates the necessary directories."""
    ensure_output_dir()
    # Verify that makedirs was called for the base directory and subdirectories
    mock_makedirs.assert_any_call(os.getenv('OUTPUT_DIR', 'outputs'), exist_ok=True)
    mock_makedirs.assert_any_call(os.path.join(os.getenv('OUTPUT_DIR', 'outputs'), 'screenshots'), exist_ok=True)
    mock_makedirs.assert_any_call(os.path.join(os.getenv('OUTPUT_DIR', 'outputs'), 'images'), exist_ok=True)

# Tests for save_to_csv
@patch('os.makedirs')
@patch('csv.DictWriter')
@patch('builtins.open', new_callable=mock_open)
def test_save_to_csv_success(mock_file_open, mock_dict_writer, mock_makedirs):
    mock_writer_instance = MagicMock()
    mock_dict_writer.return_value = mock_writer_instance

    products_data = [
        {'product_url': 'url1', 'text': 'text1', 'image_url': 'img1', 'reddit_context': {'id': 'r1', 'title': 't1', 'url': 'ru1'}},
        Product(product_id='p2', name='Product 2', affiliate_link='url2', content='text2')
    ]
    save_to_csv(products_data, 'test.csv')

    mock_makedirs.assert_called_once_with('outputs', exist_ok=True)
    mock_file_open.assert_called_once_with('outputs/test.csv', 'w', newline='')
    mock_dict_writer.assert_called_once()
    assert mock_writer_instance.writeheader.called
    assert mock_writer_instance.writerow.call_count == 2

    # Verify calls for the first product (dictionary)
    first_call_args = mock_writer_instance.writerow.call_args_list[0].args[0]
    assert first_call_args['product_url'] == 'url1'
    assert first_call_args['text_content'] == 'text1'
    assert first_call_args['image_url'] == 'img1'
    assert first_call_args['reddit_post_id'] == 'r1'
    assert first_call_args['reddit_post_title'] == 't1'
    assert first_call_args['reddit_post_url'] == 'ru1'

    # Verify calls for the second product (Product object)
    second_call_args = mock_writer_instance.writerow.call_args_list[1].args[0]
    assert second_call_args['product_url'] == 'url2'
    assert second_call_args['text_content'] == 'text2'
    assert second_call_args['image_url'] is None  # Product object doesn't have image_url by default, screenshot_path is None
    assert second_call_args['reddit_post_id'] == ''
    assert second_call_args['reddit_post_title'] == ''
    assert second_call_args['reddit_post_url'] == ''

@patch('os.makedirs')
@patch('builtins.open', side_effect=IOError('Disk full'))
def test_save_to_csv_io_error(mock_open, mock_makedirs):
    with pytest.raises(IOError):
        save_to_csv([], 'test.csv')
    mock_makedirs.assert_called_once_with('outputs', exist_ok=True)
    mock_open.assert_called_once()

# Tests for run_full_pipeline
@pytest.mark.asyncio
@patch('app.main.save_to_csv')
@patch('app.main.RedditAgent')
async def test_run_full_pipeline_success(MockRedditAgent, mock_save_to_csv):
    mock_agent_instance = MagicMock()
    MockRedditAgent.return_value = mock_agent_instance
    mock_agent_instance.find_and_create_product = AsyncMock(return_value={
        'theme': 'golf',
        'text': 'Awesome golf product',
        'color': 'Green',
        'quantity': 5,
        'reddit_context': {'title': 'Golf Thread', 'url': 'http://reddit.com/golf'},
        'product_url': 'http://zazzle.com/golf_product'
    })

    with patch('builtins.print') as mock_print:
        await run_full_pipeline()

    # Verify RedditAgent was initialized and its methods were called
    MockRedditAgent.assert_called_once()
    mock_agent_instance.find_and_create_product.assert_called_once()

    # Verify save_to_csv was called with the correct data
    mock_save_to_csv.assert_called_once()
    called_products, called_filename = mock_save_to_csv.call_args[0]
    assert called_filename == "processed_products.csv"
    assert len(called_products) == 1
    assert called_products[0]['product_url'] == 'http://zazzle.com/golf_product'
    assert called_products[0]['text'] == 'Awesome golf product'
    assert called_products[0]['theme'] == 'golf'

@pytest.mark.asyncio
@patch('app.main.save_to_csv')
@patch('app.main.RedditAgent')
async def test_run_full_pipeline_no_product_generated(MockRedditAgent, mock_save_to_csv):
    mock_agent_instance = MagicMock()
    MockRedditAgent.return_value = mock_agent_instance
    mock_agent_instance.find_and_create_product = AsyncMock(return_value=None)

    with patch('builtins.print') as mock_print:
        await run_full_pipeline()

    # Verify RedditAgent was initialized and its methods were called
    MockRedditAgent.assert_called_once()
    mock_agent_instance.find_and_create_product.assert_called_once()

    # Verify save_to_csv was not called
    mock_save_to_csv.assert_not_called()

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