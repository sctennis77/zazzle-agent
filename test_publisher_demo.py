#!/usr/bin/env python3
"""
Demo script for SubredditPublisher functionality.

This script demonstrates how the SubredditPublisher works with mock data.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.subreddit_publisher import SubredditPublisher
from app.models import GeneratedProductSchema, ProductInfoSchema, RedditPostSchema, PipelineRunSchema
from datetime import datetime, timezone


def create_mock_generated_product() -> GeneratedProductSchema:
    """Create a mock generated product for testing."""
    product_info = ProductInfoSchema(
        id=1,
        pipeline_run_id=1,
        reddit_post_id=1,
        theme="Beautiful Mountain Landscape",
        image_title="Mountain Vista",
        image_url="https://example.com/mountain-image.jpg",
        product_url="https://zazzle.com/mountain-sticker",
        affiliate_link="https://zazzle.com/mountain-sticker?ref=clouvel",
        template_id="sticker_template",
        model="dall-e-3",
        prompt_version="1.0.0",
        product_type="sticker",
        design_description="A stunning mountain landscape with golden hour lighting",
        available_actions={},
        donation_info={}
    )
    
    reddit_post = RedditPostSchema(
        id=1,
        pipeline_run_id=1,
        post_id="abc123",
        title="Just hiked Mount Rainier - the views were incredible!",
        content="Spent the weekend hiking and the sunset was absolutely breathtaking...",
        subreddit="hiking",
        url="https://reddit.com/r/hiking/comments/abc123",
        permalink="/r/hiking/comments/abc123",
        comment_summary="Amazing photos! The lighting is perfect.",
        author="hiking_enthusiast",
        score=150,
        num_comments=25
    )
    
    pipeline_run = PipelineRunSchema(
        id=1,
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        status="completed",
        summary="Successfully generated mountain landscape product",
        config={},
        metrics={},
        duration=120,
        retry_count=0,
        last_error=None,
        version="1.0.0"
    )
    
    return GeneratedProductSchema(
        product_info=product_info,
        pipeline_run=pipeline_run,
        reddit_post=reddit_post,
        usage=None
    )


def demo_publisher():
    """Demonstrate the SubredditPublisher functionality."""
    print("🎨 SubredditPublisher Demo")
    print("=" * 50)
    
    # Create publisher in dry run mode
    publisher = SubredditPublisher(dry_run=True)
    
    try:
        # Create mock data
        mock_product = create_mock_generated_product()
        
        print(f"📦 Mock Product Created:")
        print(f"  Theme: {mock_product.product_info.theme}")
        print(f"  Type: {mock_product.product_info.product_type}")
        print(f"  Original Subreddit: r/{mock_product.reddit_post.subreddit}")
        print(f"  Original Author: u/{mock_product.reddit_post.author}")
        print()
        
        # Test prepare_image_post
        print("🔧 Testing prepare_image_post...")
        prepared_post = publisher.prepare_image_post(mock_product)
        
        print(f"📝 Prepared Post:")
        print(f"  Title: {prepared_post['title']}")
        print(f"  Subreddit: r/{prepared_post['subreddit']}")
        print(f"  Image URL: {prepared_post['image_url']}")
        print(f"  Content Preview: {prepared_post['content'][:100]}...")
        print()
        
        # Test submit_prepared_image_post
        print("🚀 Testing submit_prepared_image_post...")
        submitted_post = publisher.submit_prepared_image_post(prepared_post)
        
        print(f"✅ Submitted Post Result:")
        print(f"  Action: {submitted_post['action']}")
        print(f"  Post ID: {submitted_post['post_id']}")
        print(f"  Post URL: {submitted_post['post_url']}")
        print(f"  Dry Run: {submitted_post.get('mode', 'unknown')}")
        print()
        
        # Test save_submitted_post_to_db
        print("💾 Testing save_submitted_post_to_db...")
        saved_post = publisher.save_submitted_post_to_db("1", submitted_post)
        
        print(f"💾 Saved Post Data:")
        print(f"  Product ID: {saved_post['product_id']}")
        print(f"  Subreddit: r/{saved_post['subreddit']}")
        print(f"  Reddit Post ID: {saved_post['reddit_post_id']}")
        print(f"  Submitted At: {saved_post['submitted_at']}")
        print()
        
        print("🎉 Demo completed successfully!")
        print("\n📋 Summary:")
        print("  ✅ SubredditPublisher initialized")
        print("  ✅ Image post prepared")
        print("  ✅ Post submitted to Reddit (dry run)")
        print("  ✅ Post data saved to database")
        print("  ✅ All operations completed in dry run mode")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        publisher.close()


if __name__ == "__main__":
    demo_publisher() 