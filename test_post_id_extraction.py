#!/usr/bin/env python3
"""
Test script for post ID extraction utility.
"""

from app.utils.reddit_utils import extract_post_id, validate_post_id, build_reddit_url


def test_post_id_extraction():
    """Test the post ID extraction function with various inputs."""
    
    test_cases = [
        # (input, expected_output, description)
        ("abc123", "abc123", "Simple post ID"),
        ("https://reddit.com/r/golf/comments/abc123/", "abc123", "Full Reddit URL"),
        ("https://reddit.com/r/golf/comments/abc123", "abc123", "Reddit URL without trailing slash"),
        ("https://reddit.com/r/golf/comments/abc123/some_title", "abc123", "Reddit URL with title"),
        ("https://reddit.com/comments/abc123/", "abc123", "Short Reddit URL"),
        ("https://reddit.com/comments/abc123", "abc123", "Short Reddit URL without trailing slash"),
        ("https://old.reddit.com/r/golf/comments/abc123/", "abc123", "Old Reddit URL"),
        ("https://www.reddit.com/r/golf/comments/abc123/", "abc123", "WWW Reddit URL"),
        ("", "", "Empty string"),
        ("invalid_url", "invalid_url", "Invalid URL (returns as-is)"),
        ("https://example.com/not-reddit", "https://example.com/not-reddit", "Non-Reddit URL (returns as-is)"),
    ]
    
    print("🧪 Testing Post ID Extraction")
    print("=" * 50)
    
    all_passed = True
    
    for input_text, expected, description in test_cases:
        result = extract_post_id(input_text)
        passed = result == expected
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {description}")
        print(f"    Input:  {input_text}")
        print(f"    Output: {result}")
        print(f"    Expected: {expected}")
        print()
        
        if not passed:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed!")
    else:
        print("💥 Some tests failed!")
    
    return all_passed


def test_post_id_validation():
    """Test the post ID validation function."""
    
    test_cases = [
        # (post_id, expected_valid, description)
        ("abc123", True, "Valid 6-character post ID"),
        ("abc1234", True, "Valid 7-character post ID"),
        ("abc_123", True, "Valid post ID with underscore"),
        ("abc", False, "Too short"),
        ("abc12345", False, "Too long"),
        ("abc-123", False, "Invalid character (hyphen)"),
        ("", False, "Empty string"),
        ("abc@123", False, "Invalid character (@)"),
    ]
    
    print("🧪 Testing Post ID Validation")
    print("=" * 50)
    
    all_passed = True
    
    for post_id, expected_valid, description in test_cases:
        result = validate_post_id(post_id)
        passed = result == expected_valid
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {description}")
        print(f"    Post ID: {post_id}")
        print(f"    Valid: {result}")
        print(f"    Expected: {expected_valid}")
        print()
        
        if not passed:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All validation tests passed!")
    else:
        print("💥 Some validation tests failed!")
    
    return all_passed


def test_url_building():
    """Test the Reddit URL building function."""
    
    test_cases = [
        # (subreddit, post_id, expected_url)
        ("golf", "abc123", "https://reddit.com/r/golf/comments/abc123/"),
        ("programming", "xyz789", "https://reddit.com/r/programming/comments/xyz789/"),
    ]
    
    print("🧪 Testing URL Building")
    print("=" * 50)
    
    all_passed = True
    
    for subreddit, post_id, expected_url in test_cases:
        result = build_reddit_url(subreddit, post_id)
        passed = result == expected_url
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | r/{subreddit} - {post_id}")
        print(f"    Built URL: {result}")
        print(f"    Expected:  {expected_url}")
        print()
        
        if not passed:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All URL building tests passed!")
    else:
        print("💥 Some URL building tests failed!")
    
    return all_passed


if __name__ == "__main__":
    print("🚀 Running Reddit Utils Tests")
    print()
    
    extraction_passed = test_post_id_extraction()
    print()
    
    validation_passed = test_post_id_validation()
    print()
    
    url_passed = test_url_building()
    print()
    
    print("📊 Test Summary")
    print("=" * 50)
    print(f"Post ID Extraction: {'✅ PASSED' if extraction_passed else '❌ FAILED'}")
    print(f"Post ID Validation: {'✅ PASSED' if validation_passed else '❌ FAILED'}")
    print(f"URL Building:       {'✅ PASSED' if url_passed else '❌ FAILED'}")
    print()
    
    if all([extraction_passed, validation_passed, url_passed]):
        print("🎉 All tests passed! Reddit utils are working correctly.")
        exit(0)
    else:
        print("💥 Some tests failed! Please check the implementation.")
        exit(1) 