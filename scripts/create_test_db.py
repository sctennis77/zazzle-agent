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
from app.db.models import PipelineRun, ProductInfo, RedditPost, Subreddit, Donation, SponsorTier, Sponsor
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
        # Create a test subreddit first
        subreddit = Subreddit(
            subreddit_name="test_subreddit",
            display_name="Test Subreddit",
            description="A test subreddit for testing purposes",
            subscribers=1000,
            over18=False,
            spoilers_enabled=False
        )
        db.add(subreddit)
        db.commit()
        db.refresh(subreddit)

        # Create sponsor tiers
        bronze_tier = SponsorTier(
            name="Bronze",
            min_amount=5.00,
            benefits="Basic sponsorship benefits",
            description="Bronze level sponsorship"
        )
        silver_tier = SponsorTier(
            name="Silver", 
            min_amount=10.00,
            benefits="Enhanced sponsorship benefits",
            description="Silver level sponsorship"
        )
        gold_tier = SponsorTier(
            name="Gold",
            min_amount=25.00,
            benefits="Premium sponsorship benefits", 
            description="Gold level sponsorship"
        )
        
        db.add_all([bronze_tier, silver_tier, gold_tier])
        db.commit()
        db.refresh(bronze_tier)
        db.refresh(silver_tier)
        db.refresh(gold_tier)

        # Create test donations (both sponsor and commission types)
        sponsor_donation = Donation(
            stripe_payment_intent_id="pi_test_sponsor_123",
            amount_cents=1000,  # $10.00
            amount_usd=10.00,
            currency="usd",
            status="succeeded",
            customer_email="sponsor@test.com",
            customer_name="Test Sponsor",
            message="Supporting the community!",
            subreddit_id=subreddit.id,
            reddit_username="test_sponsor",
            is_anonymous=False,
            donation_type="sponsor"
        )
        
        commission_donation = Donation(
            stripe_payment_intent_id="pi_test_commission_456",
            amount_cents=2500,  # $25.00
            amount_usd=25.00,
            currency="usd", 
            status="succeeded",
            customer_email="commissioner@test.com",
            customer_name="Test Commissioner",
            message="Please create something awesome!",
            subreddit_id=subreddit.id,
            reddit_username="test_commissioner",
            is_anonymous=False,
            donation_type="commission",
            post_id="test_post_123",
            commission_message="Commissioned by a generous supporter!"
        )
        
        db.add_all([sponsor_donation, commission_donation])
        db.commit()
        db.refresh(sponsor_donation)
        db.refresh(commission_donation)

        # Create sponsors linked to donations
        sponsor = Sponsor(
            donation_id=sponsor_donation.id,
            tier_id=silver_tier.id,
            subreddit_id=subreddit.id,
            status="active"
        )
        
        db.add(sponsor)
        db.commit()
        db.refresh(sponsor)

        # Create a pipeline run
        pipeline_run = PipelineRun(
            status=PipelineStatus.COMPLETED.value,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            summary="Test pipeline run completed successfully",
            config={"test": True},
            metrics={"products_generated": 3},
            duration=120,
            retry_count=0,
            version="1.0.0"
        )
        db.add(pipeline_run)
        db.commit()
        db.refresh(pipeline_run)

        # Create a test Reddit post
        reddit_post = RedditPost(
            post_id="test_post_123",
            title="Test Post Title",
            content="This is a test post content for testing the interaction agent.",
            subreddit_id=subreddit.id,
            score=1000,
            url="https://reddit.com/r/test_subreddit/comments/test_post_123",
            permalink="/r/test_subreddit/comments/test_post_123/test_post_title/",
            pipeline_run_id=pipeline_run.id,
            comment_summary="Test comment summary",
            author="test_user",
            num_comments=50
        )
        db.add(reddit_post)
        db.commit()
        db.refresh(reddit_post)

        # Create test products
        products = []
        for i in range(3):
            product = ProductInfo(
                theme=f"Test Product {i+1}",
                image_title=f"Test Image {i+1}",
                product_url=f"https://zazzle.com/test_product_{i+1}",
                affiliate_link=f"https://zazzle.com/test_product_{i+1}?affiliate_id=test",
                template_id=f"template_{i+1}",
                model="dall-e-3",
                prompt_version="1.0",
                product_type="t-shirt",
                design_description=f"This is test product {i+1} description",
                reddit_post_id=reddit_post.id,
                pipeline_run_id=pipeline_run.id,
            )
            db.add(product)
            products.append(product)

        db.commit()

        print(f"✅ Created test database successfully!")
        print(f"   - Subreddit ID: {subreddit.id}")
        print(f"   - Pipeline run ID: {pipeline_run.id}")
        print(f"   - Reddit post ID: {reddit_post.id}")
        print(f"   - Product IDs: {[p.id for p in products]}")
        print(f"   - Sponsor donation ID: {sponsor_donation.id}")
        print(f"   - Commission donation ID: {commission_donation.id}")
        print(f"   - Sponsor ID: {sponsor.id}")

        if db_path:
            print(f"   - Database file: {db_path}")

        return {
            "subreddit_id": subreddit.id,
            "pipeline_run_id": pipeline_run.id,
            "reddit_post_id": reddit_post.id,
            "product_ids": [p.id for p in products],
            "sponsor_donation_id": sponsor_donation.id,
            "commission_donation_id": commission_donation.id,
            "sponsor_id": sponsor.id,
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
