#!/usr/bin/env python3
"""
Script to create test data for the interaction agent.
"""

import os
import sys
from datetime import datetime, timezone

from app.db.database import SessionLocal, init_db
from app.db.models import PipelineRun, ProductInfo, RedditPost
from app.pipeline_status import PipelineStatus


def create_test_data():
    """Create test data for the interaction agent."""

    # Initialize database
    init_db()

    # Create database session
    db = SessionLocal()

    try:
        # Create a pipeline run
        pipeline_run = PipelineRun(
            status=PipelineStatus.COMPLETED.value,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            subreddit="test_subreddit",
        )
        db.add(pipeline_run)
        db.commit()
        db.refresh(pipeline_run)

        # Create a test Reddit post
        reddit_post = RedditPost(
            reddit_id="test_post_123",
            title="Test Post Title",
            content="This is a test post content for testing the interaction agent.",
            score=1000,
            subreddit="test_subreddit",
            url="https://reddit.com/r/test_subreddit/comments/test_post_123",
            pipeline_run_id=pipeline_run.id,
            comment_summary="Test comment summary",
        )
        db.add(reddit_post)
        db.commit()
        db.refresh(reddit_post)

        # Create test products
        products = []
        for i in range(3):
            product = ProductInfo(
                title=f"Test Product {i+1}",
                description=f"This is test product {i+1} description",
                image_url=f"https://example.com/test_image_{i+1}.jpg",
                affiliate_link=f"https://zazzle.com/test_product_{i+1}?affiliate_id=test",
                reddit_post_id=reddit_post.id,
                pipeline_run_id=pipeline_run.id,
            )
            db.add(product)
            products.append(product)

        db.commit()

        print(f"✅ Created test data:")
        print(f"   - Pipeline run ID: {pipeline_run.id}")
        print(f"   - Reddit post ID: {reddit_post.id}")
        print(f"   - Product IDs: {[p.id for p in products]}")

        return {
            "pipeline_run_id": pipeline_run.id,
            "reddit_post_id": reddit_post.id,
            "product_ids": [p.id for p in products],
        }

    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_data()
