#!/usr/bin/env python3
"""
Script to check the Clouvel promoter Reddit account activity and status.
"""

import os
from datetime import datetime

import praw


def check_reddit_account():
    """Check the promoter agent Reddit account for activity and status."""

    # Get credentials from environment
    client_id = os.getenv("PROMOTER_AGENT_CLIENT_ID")
    client_secret = os.getenv("PROMOTER_AGENT_CLIENT_SECRET")
    username = os.getenv("PROMOTER_AGENT_USERNAME")
    password = os.getenv("PROMOTER_AGENT_PASSWORD")
    user_agent = os.getenv("PROMOTER_AGENT_USER_AGENT")

    if not all([client_id, client_secret, username, password, user_agent]):
        print("❌ Missing required environment variables")
        return

    try:
        # Initialize Reddit client
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent,
        )

        # Get the authenticated user
        user = reddit.user.me()
        print(f"✅ Successfully authenticated as: u/{user.name}")
        print(f"📊 Account created: {datetime.fromtimestamp(user.created_utc)}")
        print(f"🏆 Comment karma: {user.comment_karma}")
        print(f"🏆 Link karma: {user.link_karma}")
        print(f"📧 Email verified: {user.has_verified_email}")
        print(f"🔒 Account suspended: {user.is_suspended}")
        print()

        # Check recent comments
        print("📝 Recent comments from account:")
        print("-" * 50)

        comment_count = 0
        for comment in user.comments.new(limit=10):
            comment_count += 1
            created_time = datetime.fromtimestamp(comment.created_utc)
            print(f"Comment {comment_count}:")
            print(f"  ID: {comment.id}")
            print(f"  Subreddit: r/{comment.subreddit}")
            print(f"  Post: {comment.submission.id}")
            print(f"  Created: {created_time}")
            print(f"  Score: {comment.score}")
            print(f"  Text preview: {comment.body[:100]}...")
            print(f"  URL: https://reddit.com{comment.permalink}")
            print()

        if comment_count == 0:
            print("⚠️  No comments found in account history!")
            print("This could indicate:")
            print("- Account is shadowbanned")
            print("- Comments are being filtered by Reddit")
            print("- All comments have been removed")

        # Check specifically for the comment in question
        print("🔍 Searching for specific comment n3pqnd4...")
        try:
            specific_comment = reddit.comment("n3pqnd4")
            print(f"✅ Found comment n3pqnd4:")
            print(f"  Author: {specific_comment.author}")
            print(f"  Body: {specific_comment.body}")
            print(f"  Score: {specific_comment.score}")
            print(f"  Created: {datetime.fromtimestamp(specific_comment.created_utc)}")
        except Exception as e:
            print(f"❌ Could not fetch comment n3pqnd4: {e}")

        # Check if we can access the specific post
        print("\n🔍 Checking access to post 1m2cufu...")
        try:
            post = reddit.submission("1m2cufu")
            print(f"✅ Can access post: {post.title}")
            print(f"  Subreddit: r/{post.subreddit}")
            print(f"  Score: {post.score}")
            print(f"  Comments: {post.num_comments}")
        except Exception as e:
            print(f"❌ Could not access post 1m2cufu: {e}")

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("This could indicate:")
        print("- Incorrect credentials")
        print("- Account is suspended")
        print("- Reddit API issues")


if __name__ == "__main__":
    check_reddit_account()
