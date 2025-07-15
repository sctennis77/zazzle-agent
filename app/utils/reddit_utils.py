"""
Reddit utility functions for parsing and processing Reddit data.
"""

import re
from typing import Optional


def extract_post_id(input_text: str) -> str:
    """
    Extract Reddit post ID from various input formats.

    This function handles the same patterns as the frontend extractPostId function:
    - Full Reddit URLs: https://reddit.com/r/subreddit/comments/post_id/...
    - Short Reddit URLs: https://reddit.com/comments/post_id/...
    - Just the post ID: abc123

    Args:
        input_text: The input text that may contain a Reddit post ID or URL

    Returns:
        str: The extracted post ID, or the original input if no pattern matches
    """
    if not input_text:
        return ""

    # Handle various Reddit URL formats
    patterns = [
        r"reddit\.com/r/[^/]+/comments/([a-zA-Z0-9]+)",  # Full subreddit URL
        r"reddit\.com/comments/([a-zA-Z0-9]+)",  # Short URL
        r"^([a-zA-Z0-9]+)$",  # Just the post ID
    ]

    for pattern in patterns:
        match = re.search(pattern, input_text)
        if match:
            return match.group(1)

    # Return as-is if no pattern matches
    return input_text


def validate_post_id(post_id: str) -> bool:
    """
    Validate that a post ID follows Reddit's format.

    Args:
        post_id: The post ID to validate

    Returns:
        bool: True if the post ID is valid, False otherwise
    """
    if not post_id:
        return False

    # Reddit post IDs are typically 6-7 characters long and contain alphanumeric characters
    # They may also contain underscores
    pattern = r"^[a-zA-Z0-9_]{6,7}$"
    return bool(re.match(pattern, post_id))


def build_reddit_url(subreddit: str, post_id: str) -> str:
    """
    Build a Reddit URL from subreddit and post ID.

    Args:
        subreddit: The subreddit name
        post_id: The post ID

    Returns:
        str: The full Reddit URL
    """
    return f"https://reddit.com/r/{subreddit}/comments/{post_id}/"
