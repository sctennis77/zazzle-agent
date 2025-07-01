#!/usr/bin/env python3
"""
Simple test script for the commission validation endpoint with mocked Reddit API.
"""

import asyncio
import json
from unittest.mock import Mock, patch
from app.services.commission_validator import CommissionValidator, ValidationResult


async def test_validation_endpoint_simple():
    """Test the commission validation endpoint with mocked Reddit API."""
    
    print("🧪 Testing Commission Validation Endpoint (Mocked)")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        {
            "name": "Random Random Commission",
            "commission_type": "random_random",
            "expected_valid": True,
            "mock_subreddit": "hiking"
        },
        {
            "name": "Random Subreddit Commission (valid subreddit)",
            "commission_type": "random_subreddit",
            "subreddit": "hiking",
            "expected_valid": True
        },
        {
            "name": "Random Subreddit Commission (invalid subreddit)",
            "commission_type": "random_subreddit",
            "subreddit": "nonexistent_subreddit_12345",
            "expected_valid": False
        },
        {
            "name": "Specific Post Commission (missing post_id)",
            "commission_type": "specific_post",
            "expected_valid": False
        },
        {
            "name": "Specific Post Commission (valid post_id)",
            "commission_type": "specific_post",
            "post_id": "abc123",
            "expected_valid": True
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 40)
        
        try:
            # Mock the Reddit API calls
            with patch('app.services.commission_validator.pick_subreddit') as mock_pick_subreddit, \
                 patch('app.services.commission_validator.CommissionValidator._validate_subreddit_exists') as mock_validate_subreddit, \
                 patch('app.services.commission_validator.CommissionValidator._find_and_validate_post') as mock_find_post, \
                 patch('app.services.commission_validator.CommissionValidator._validate_specific_post') as mock_validate_specific:
                
                # Setup mocks based on test case
                if test_case["commission_type"] == "random_random":
                    mock_pick_subreddit.return_value = test_case.get("mock_subreddit", "hiking")
                    mock_find_post.return_value = ValidationResult(
                        valid=True,
                        subreddit="hiking",
                        subreddit_id=1,
                        post_id="abc123",
                        post_title="Amazing hiking adventure!",
                        post_url="https://reddit.com/r/hiking/abc123",
                        post_content="Just finished this incredible hike...",
                        commission_type="random_random"
                    )
                elif test_case["commission_type"] == "random_subreddit":
                    if test_case.get("subreddit") == "nonexistent_subreddit_12345":
                        mock_validate_subreddit.return_value = False
                    else:
                        mock_validate_subreddit.return_value = True
                        mock_find_post.return_value = ValidationResult(
                            valid=True,
                            subreddit=test_case["subreddit"],
                            subreddit_id=1,
                            post_id="def456",
                            post_title="Great post from subreddit!",
                            post_url="https://reddit.com/r/hiking/def456",
                            post_content="This is a great post...",
                            commission_type="random_subreddit"
                        )
                elif test_case["commission_type"] == "specific_post":
                    if test_case.get("post_id"):
                        mock_validate_specific.return_value = ValidationResult(
                            valid=True,
                            subreddit="hiking",
                            subreddit_id=1,
                            post_id=test_case["post_id"],
                            post_title="Specific post title!",
                            post_url=f"https://reddit.com/r/hiking/{test_case['post_id']}",
                            post_content="This is the specific post content...",
                            commission_type="specific_post"
                        )
                    else:
                        mock_validate_specific.return_value = ValidationResult(
                            valid=False,
                            error="Post ID or URL is required for specific_post commission"
                        )
                
                # Initialize validator
                validator = CommissionValidator()
                
                # Call validation
                result = await validator.validate_commission(
                    commission_type=test_case["commission_type"],
                    subreddit=test_case.get("subreddit"),
                    post_id=test_case.get("post_id"),
                    post_url=test_case.get("post_url")
                )
                
                # Print result
                print(f"✅ Valid: {result.valid}")
                if result.valid:
                    print(f"📱 Subreddit: {result.subreddit}")
                    print(f"🆔 Post ID: {result.post_id}")
                    print(f"📝 Post Title: {result.post_title}")
                    print(f"🔗 Post URL: {result.post_url}")
                    print(f"🎨 Commission Type: {result.commission_type}")
                else:
                    print(f"❌ Error: {result.error}")
                
                # Check if result matches expectation
                if result.valid == test_case["expected_valid"]:
                    print("✅ Test PASSED")
                else:
                    print(f"❌ Test FAILED - Expected {test_case['expected_valid']}, got {result.valid}")
                    
        except Exception as e:
            print(f"❌ Test ERROR: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🏁 Validation endpoint test completed!")


if __name__ == "__main__":
    asyncio.run(test_validation_endpoint_simple()) 