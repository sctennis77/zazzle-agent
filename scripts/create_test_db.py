#!/usr/bin/env python3
"""
Script to create test databases with sample data for testing.
This script can be used to set up test databases for different test scenarios.
"""

import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import SessionLocal, init_db
from app.db.models import PipelineRun, ProductInfo, RedditPost
from app.pipeline_status import PipelineStatus


def create_test_database(db_path=None):
    """
    Create a test database with sample data.

    Args:
        db_path (str, optional): Path to the test database file.
                               If None, uses default test database path.
    """

    if db_path:
        # Set the database URL for the test database
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # Initialize database
    print("Initializing test database...")
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

        print(f"✅ Created test database successfully!")
        print(f"   - Pipeline run ID: {pipeline_run.id}")
        print(f"   - Reddit post ID: {reddit_post.id}")
        print(f"   - Product IDs: {[p.id for p in products]}")

        if db_path:
            print(f"   - Database file: {db_path}")

        return {
            "pipeline_run_id": pipeline_run.id,
            "reddit_post_id": reddit_post.id,
            "product_ids": [p.id for p in products],
        }

    except Exception as e:
        print(f"❌ Error creating test database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_interaction_agent_test_db():
    """Create a specific test database for interaction agent tests."""
    test_db_path = "test_interaction_agent.db"
    print(f"Creating interaction agent test database: {test_db_path}")
    return create_test_database(test_db_path)


def backup_existing_db(db_path):
    """Create a backup of an existing database."""
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(db_path, backup_path)
        print(f"📦 Backed up existing database to: {backup_path}")
        return backup_path
    return None


def main():
    """Main function to create test databases."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create test databases with sample data"
    )
    parser.add_argument("--db-path", help="Path to the test database file")
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup existing database before creating new one",
    )
    parser.add_argument(
        "--interaction-agent",
        action="store_true",
        help="Create test database for interaction agent",
    )

    args = parser.parse_args()

    try:
        if args.interaction_agent:
            # Create interaction agent test database
            if args.backup:
                backup_existing_db("test_interaction_agent.db")
            create_interaction_agent_test_db()
        elif args.db_path:
            # Create custom test database
            if args.backup:
                backup_existing_db(args.db_path)
            create_test_database(args.db_path)
        else:
            # Create default test database
            if args.backup:
                backup_existing_db("test_interaction_agent.db")
            create_interaction_agent_test_db()

    except Exception as e:
        print(f"❌ Failed to create test database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
