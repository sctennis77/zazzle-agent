#!/usr/bin/env python3
"""
Test different ways to access and verify the comment n3pqnd4 visibility.
"""

import os
from datetime import datetime

import praw
import requests


def test_comment_visibility():
    """Test various ways to check comment visibility and URL formats."""

    # Reddit credentials
    client_id = os.getenv("PROMOTER_AGENT_CLIENT_ID")
    client_secret = os.getenv("PROMOTER_AGENT_CLIENT_SECRET")
    username = os.getenv("PROMOTER_AGENT_USERNAME")
    password = os.getenv("PROMOTER_AGENT_PASSWORD")
    user_agent = os.getenv("PROMOTER_AGENT_USER_AGENT")

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        user_agent=user_agent,
    )

    comment_id = "n3pqnd4"
    post_id = "1m2cufu"

    print("🔍 Testing Comment Visibility for n3pqnd4")
    print("=" * 50)

    # Test 1: Direct comment access via PRAW
    try:
        comment = reddit.comment(comment_id)
        print(f"✅ PRAW Comment Access:")
        print(f"   ID: {comment.id}")
        print(f"   Author: {comment.author}")
        print(f"   Score: {comment.score}")
        print(f"   Body: {comment.body[:100]}...")
        print(f"   Permalink: https://reddit.com{comment.permalink}")
        print()
    except Exception as e:
        print(f"❌ PRAW Comment Access Failed: {e}")
        print()

    # Test 2: Check if comment shows up in post's comments
    try:
        submission = reddit.submission(post_id)
        print(f"📋 Searching in Post Comments (Total: {submission.num_comments}):")

        submission.comments.replace_more(limit=0)  # Get all comments
        found_comment = False

        def search_comments(comment_list, depth=0):
            global found_comment
            for comment in comment_list:
                if hasattr(comment, "id") and comment.id == comment_id:
                    print(f"   ✅ Found comment {comment_id} at depth {depth}")
                    print(f"   Author: {comment.author}")
                    print(f"   Score: {comment.score}")
                    return True
                if hasattr(comment, "replies"):
                    if search_comments(comment.replies, depth + 1):
                        return True
            return False

        found_comment = search_comments(submission.comments)
        if not found_comment:
            print(f"   ❌ Comment {comment_id} NOT found in post's comment tree")
        print()

    except Exception as e:
        print(f"❌ Post Comment Search Failed: {e}")
        print()

    # Test 3: Test different URL formats
    url_formats = [
        f"https://www.reddit.com/r/interestingasfuck/comments/{post_id}/comment/{comment_id}/",
        f"https://reddit.com/r/interestingasfuck/comments/{post_id}/comment/{comment_id}/",
        f"https://www.reddit.com/r/interestingasfuck/comments/{post_id}/man_protects_himself_from_a_pitbull_attack_mexico/{comment_id}/",
        f"https://reddit.com/r/interestingasfuck/comments/{post_id}/man_protects_himself_from_a_pitbull_attack_mexico/{comment_id}/",
        f"https://www.reddit.com/comments/{comment_id}/",
        f"https://reddit.com/comments/{comment_id}/",
    ]

    print("🔗 Testing Different URL Formats:")
    for i, url in enumerate(url_formats, 1):
        try:
            response = requests.get(url, headers={"User-Agent": "TestScript/1.0"})
            if response.status_code == 200:
                if "Sorry, this post was removed by Reddit" in response.text:
                    print(f"   {i}. ❌ {url} - Post removed by Reddit")
                elif (
                    f'data-testid="comment-{comment_id}"' in response.text
                    or comment_id in response.text
                ):
                    print(f"   {i}. ✅ {url} - Comment found in HTML")
                else:
                    print(f"   {i}. ⚠️  {url} - No comment found in response")
            else:
                print(f"   {i}. ❌ {url} - HTTP {response.status_code}")
        except Exception as e:
            print(f"   {i}. ❌ {url} - Error: {e}")
    print()

    # Test 4: Check comment visibility with Reddit JSON API
    print("📊 Testing Reddit JSON API:")
    json_urls = [
        f"https://www.reddit.com/r/interestingasfuck/comments/{post_id}.json",
        f"https://www.reddit.com/comments/{comment_id}.json",
    ]

    for url in json_urls:
        try:
            response = requests.get(url, headers={"User-Agent": "TestScript/1.0"})
            if response.status_code == 200:
                data = response.json()
                if comment_id in str(data):
                    print(f"   ✅ {url} - Comment found in JSON")
                else:
                    print(f"   ❌ {url} - Comment NOT found in JSON")
            else:
                print(f"   ❌ {url} - HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ {url} - Error: {e}")
    print()

    # Test 5: Check if comment is visible to logged out users
    print("👤 Testing Logged-out Visibility:")
    try:
        # Create unauthenticated reddit instance
        public_reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="PublicCheck/1.0",
        )

        public_comment = public_reddit.comment(comment_id)
        print(f"   ✅ Public access to comment successful")
        print(f"   Author: {public_comment.author}")
        print(f"   Score: {public_comment.score}")
    except Exception as e:
        print(f"   ❌ Public access failed: {e}")
    print()

    # Test 6: Generate the exact URL that should work
    try:
        comment = reddit.comment(comment_id)
        correct_url = f"https://www.reddit.com{comment.permalink}"
        print(f"🎯 Correct URL from PRAW:")
        print(f"   {correct_url}")

        # Test this URL
        response = requests.get(correct_url, headers={"User-Agent": "TestScript/1.0"})
        if response.status_code == 200:
            if comment_id in response.text:
                print(f"   ✅ Comment visible at correct URL")
            else:
                print(f"   ❌ Comment NOT visible at correct URL")
        else:
            print(f"   ❌ HTTP {response.status_code} for correct URL")

    except Exception as e:
        print(f"   ❌ Error getting correct URL: {e}")


if __name__ == "__main__":
    test_comment_visibility()
