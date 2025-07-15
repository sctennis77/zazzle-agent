#!/usr/bin/env python3
"""
Test script for the commission validation endpoint.
"""

import asyncio
import json

from app.services.commission_validator import CommissionValidator


async def test_validation_endpoint():
    """Test the commission validation endpoint."""

    print("🧪 Testing Commission Validation Endpoint")
    print("=" * 50)

    # Initialize validator
    validator = CommissionValidator()

    # Test cases
    test_cases = [
        {
            "name": "Random Random Commission",
            "commission_type": "random_random",
            "expected_valid": True,
        },
        {
            "name": "Random Subreddit Commission (valid subreddit)",
            "commission_type": "random_subreddit",
            "subreddit": "hiking",
            "expected_valid": True,
        },
        {
            "name": "Random Subreddit Commission (invalid subreddit)",
            "commission_type": "random_subreddit",
            "subreddit": "nonexistent_subreddit_12345",
            "expected_valid": False,
        },
        {
            "name": "Specific Post Commission (missing post_id)",
            "commission_type": "specific_post",
            "expected_valid": False,
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 30)

        try:
            # Call validation
            result = await validator.validate_commission(
                commission_type=test_case["commission_type"],
                subreddit=test_case.get("subreddit"),
                post_id=test_case.get("post_id"),
                post_url=test_case.get("post_url"),
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
                print(
                    f"❌ Test FAILED - Expected {test_case['expected_valid']}, got {result.valid}"
                )

        except Exception as e:
            print(f"❌ Test ERROR: {str(e)}")

    print("\n" + "=" * 50)
    print("🏁 Validation endpoint test completed!")


if __name__ == "__main__":
    asyncio.run(test_validation_endpoint())
