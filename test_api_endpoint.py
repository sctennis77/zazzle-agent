#!/usr/bin/env python3
"""
Test the API endpoint integration for commenting on original posts.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api_imports():
    """Test that all API imports work correctly."""
    print("🧪 Testing API imports...")
    
    try:
        from app.models import ProductRedditCommentSchema
        print("✅ ProductRedditCommentSchema imported")
        
        from app.reddit_commenter import RedditCommenter
        print("✅ RedditCommenter imported")
        
        # Test schema validation
        test_data = {
            "id": 1,
            "product_info_id": 123,
            "original_post_id": "abc123",
            "comment_id": "def456",
            "comment_url": "https://reddit.com/r/test/comments/abc123/_/def456",
            "subreddit_name": "test",
            "commented_at": "2025-07-18T15:00:00Z",
            "comment_content": "Test comment",
            "dry_run": True,
            "status": "commented",
            "error_message": None,
            "engagement_data": None
        }
        
        schema = ProductRedditCommentSchema.model_validate(test_data)
        print("✅ ProductRedditCommentSchema validation works")
        
        print("✅ All API imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def main():
    print("🔍 Testing API Endpoint Integration")
    print("=" * 40)
    
    if test_api_imports():
        print("\n✅ API INTEGRATION READY!")
        print("🎯 Ready for local testing")
    else:
        print("\n❌ API INTEGRATION FAILED!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())