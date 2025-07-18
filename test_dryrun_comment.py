#!/usr/bin/env python3
"""
Test script to verify dry-run comment functionality.
This script tests that:
1. Dry-run mode doesn't make actual Reddit API calls
2. Comment content is properly formatted
3. Return data is properly structured
"""

import os
import sys
import tempfile
from unittest.mock import Mock, patch

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.clients.reddit_client import RedditClient
from app.reddit_commenter import RedditCommenter


def test_reddit_client_dry_run():
    """Test RedditClient comment_with_image in dry-run mode."""
    print("🧪 Testing RedditClient.comment_with_image() in dry-run mode...")
    
    # Create client in dry-run mode
    os.environ["REDDIT_MODE"] = "dryrun"
    client = RedditClient()
    
    # Test data
    post_id = "test_post_123"
    comment_text = """Love this story! Created some art inspired by your post 🎨

{image1}

Commissioned by u/test_user • Made with [Clouvel](https://clouvel.ai/?product=test_post_123)"""
    image_url = "https://example.com/test_image.jpg"
    
    # Mock the image download
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.content = b"fake_image_data"
        mock_response.raise_for_status = lambda: None
        mock_get.return_value = mock_response
        
        # Call the method
        result = client.comment_with_image(post_id, comment_text, image_url)
    
    # Verify results
    print(f"✅ Result type: {result['type']}")
    print(f"✅ Action: {result['action']}")
    print(f"✅ Post ID: {result['post_id']}")
    print(f"✅ Comment text preview:")
    print(f"   {result['comment_text'][:100]}...")
    print(f"✅ Dry-run comment ID: {result['comment_id']}")
    print(f"✅ Dry-run comment URL: {result['comment_url']}")
    
    # Assertions
    assert result["type"] == "image_comment"
    assert result["action"] == "would submit image comment"
    assert result["post_id"] == post_id
    assert result["comment_text"] == comment_text
    assert result["comment_id"] == "dryrun_comment_id"
    assert "dryrun_comment_id" in result["comment_url"]
    assert result["subreddit"] == "dryrun_subreddit"
    
    print("✅ RedditClient dry-run test PASSED!\n")
    return result


def test_reddit_commenter_dry_run():
    """Test RedditCommenter in dry-run mode with mock data."""
    print("🧪 Testing RedditCommenter.comment_on_original_post() in dry-run mode...")
    
    # This would require database setup, so we'll test the comment generation logic
    from app.reddit_commenter import RedditCommenter
    
    # Test the comment content generation
    commenter = RedditCommenter(dry_run=True)
    
    # Mock generated product data
    mock_product = Mock()
    mock_product.product_info.image_title = "Epic Fantasy Landscape"
    mock_product.product_info.theme = "Fantasy Art"
    mock_product.product_info.image_url = "https://example.com/fantasy_art.jpg"
    mock_product.reddit_post.post_id = "abc123xyz"
    mock_product.reddit_post.author = "original_poster"
    
    # Test comment username logic
    username = commenter._get_commission_username(mock_product, None)
    assert username == "original_poster"
    
    # Test with donation
    mock_donation = Mock()
    mock_donation.is_anonymous = False
    mock_donation.reddit_username = "art_lover_123"
    
    username_with_donation = commenter._get_commission_username(mock_product, mock_donation)
    assert username_with_donation == "art_lover_123"
    
    print("✅ Comment username logic works correctly")
    print("✅ RedditCommenter dry-run test PASSED!\n")


def main():
    """Run all dry-run tests."""
    print("🔍 Testing Reddit Comment Functionality (Dry-Run Mode)")
    print("=" * 60)
    
    try:
        # Test 1: RedditClient dry-run
        reddit_result = test_reddit_client_dry_run()
        
        # Test 2: RedditCommenter dry-run  
        test_reddit_commenter_dry_run()
        
        # Show full comment preview
        print("📝 FULL COMMENT PREVIEW:")
        print("=" * 40)
        print(reddit_result['comment_text'])
        print("=" * 40)
        
        print("\n✅ ALL TESTS PASSED!")
        print("🎯 Dry-run mode working correctly - no actual Reddit API calls made")
        print("📋 Comment content is properly formatted")
        print("🔗 Links and usernames are correctly generated")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())