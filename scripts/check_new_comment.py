#!/usr/bin/env python3
"""
Check the new comment n3pshaa and verify its visibility.
"""

import os
import praw
import requests
from datetime import datetime

def check_new_comment():
    """Check the new comment n3pshaa for visibility and details."""
    
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
    
    comment_id = "n3pshaa"
    post_id = "1m2g6r1"
    subreddit = "DunderMifflin"
    
    print(f"🔍 Checking New Comment {comment_id}")
    print("=" * 50)
    
    # Check the comment directly
    try:
        comment = reddit.comment(comment_id)
        print(f"✅ Comment Details:")
        print(f"   ID: {comment.id}")
        print(f"   Author: {comment.author}")
        print(f"   Subreddit: r/{comment.subreddit}")
        print(f"   Post ID: {comment.submission.id}")
        print(f"   Created: {datetime.fromtimestamp(comment.created_utc)}")
        print(f"   Score: {comment.score}")
        print(f"   Body: {comment.body}")
        print(f"   Permalink: https://reddit.com{comment.permalink}")
        print()
        
        # Get the correct URL format
        correct_url = f"https://www.reddit.com{comment.permalink}"
        print(f"🎯 Correct URL: {correct_url}")
        
        # Test the provided URL vs correct URL
        provided_url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/comment/{comment_id}/"
        print(f"🔗 Provided URL: {provided_url}")
        
        # Check if both URLs work
        for name, url in [("Correct", correct_url), ("Provided", provided_url)]:
            try:
                response = requests.get(url, headers={'User-Agent': 'TestScript/1.0'})
                if response.status_code == 200:
                    if comment_id in response.text:
                        print(f"   ✅ {name} URL works - Comment visible")
                    else:
                        print(f"   ⚠️  {name} URL loads but comment not found")
                else:
                    print(f"   ❌ {name} URL - HTTP {response.status_code}")
            except Exception as e:
                print(f"   ❌ {name} URL error: {e}")
        print()
        
    except Exception as e:
        print(f"❌ Could not access comment {comment_id}: {e}")
        print()
    
    # Check if comment appears in post's comment tree
    try:
        submission = reddit.submission(post_id)
        print(f"📋 Post: {submission.title}")
        print(f"   Subreddit: r/{submission.subreddit}")
        print(f"   Total comments: {submission.num_comments}")
        
        submission.comments.replace_more(limit=0)
        found_in_tree = False
        
        def search_comments(comment_list, depth=0):
            for comment in comment_list:
                if hasattr(comment, 'id') and comment.id == comment_id:
                    print(f"   ✅ Found comment in post tree at depth {depth}")
                    print(f"   Score in tree: {comment.score}")
                    return True
                if hasattr(comment, 'replies'):
                    if search_comments(comment.replies, depth + 1):
                        return True
            return False
        
        found_in_tree = search_comments(submission.comments)
        if not found_in_tree:
            print(f"   ❌ Comment {comment_id} NOT found in post's comment tree")
            print("   This indicates shadow removal/filtering")
        print()
        
    except Exception as e:
        print(f"❌ Error checking post tree: {e}")
        print()
    
    # Get all recent comments from the Clouvel account
    try:
        user = reddit.user.me()
        print(f"📝 Recent comments from u/{user.name}:")
        print("-" * 30)
        
        for i, comment in enumerate(user.comments.new(limit=5), 1):
            created_time = datetime.fromtimestamp(comment.created_utc)
            print(f"{i}. Comment {comment.id}")
            print(f"   Subreddit: r/{comment.subreddit}")
            print(f"   Post: {comment.submission.id}")
            print(f"   Created: {created_time}")
            print(f"   Score: {comment.score}")
            print(f"   URL: https://reddit.com{comment.permalink}")
            print(f"   Preview: {comment.body[:100]}...")
            print()
            
    except Exception as e:
        print(f"❌ Error getting recent comments: {e}")

if __name__ == "__main__":
    check_new_comment()