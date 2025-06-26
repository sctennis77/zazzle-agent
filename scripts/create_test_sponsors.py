#!/usr/bin/env python3
"""
Script to create test sponsors with different tiers for testing the sponsor display functionality.
"""

from app.db.database import SessionLocal
from app.db.models import Sponsor, Donation, SponsorTier
from decimal import Decimal

def create_test_sponsors():
    """Create test sponsors with different tiers."""
    db = SessionLocal()
    
    try:
        # Get existing tiers
        tiers = db.query(SponsorTier).all()
        print(f"Found {len(tiers)} sponsor tiers:")
        for tier in tiers:
            print(f"  - {tier.name}: ${tier.min_amount}")
        
        # Create test donations and sponsors
        test_data = [
            {
                "reddit_username": "golf_lover",
                "tier_name": "Gold",
                "amount": Decimal("75.00"),
                "is_anonymous": False,
                "subreddit": "golf"
            },
            {
                "reddit_username": "anonymous_supporter",
                "tier_name": "Bronze",
                "amount": Decimal("10.00"),
                "is_anonymous": True,
                "subreddit": "golf"
            },
            {
                "reddit_username": "premium_user",
                "tier_name": "Platinum",
                "amount": Decimal("150.00"),
                "is_anonymous": False,
                "subreddit": "all"
            }
        ]
        
        created_count = 0
        for sponsor_info in test_data:
            # Find the tier
            tier = db.query(SponsorTier).filter_by(name=sponsor_info["tier_name"]).first()
            if not tier:
                print(f"Tier {sponsor_info['tier_name']} not found, skipping...")
                continue
            
            # Create donation
            donation = Donation(
                stripe_payment_intent_id=f"pi_test_{created_count + 100}",
                amount_cents=int(sponsor_info["amount"] * 100),
                amount_usd=sponsor_info["amount"],
                currency="usd",
                status="succeeded",
                customer_email=f"{sponsor_info['reddit_username']}@example.com",
                customer_name=sponsor_info["reddit_username"],
                subreddit=sponsor_info["subreddit"],
                reddit_username=sponsor_info["reddit_username"],
                is_anonymous=sponsor_info["is_anonymous"]
            )
            db.add(donation)
            db.flush()  # Get the donation ID
            
            # Create sponsor
            sponsor = Sponsor(
                donation_id=donation.id,
                tier_id=tier.id,
                subreddit=sponsor_info["subreddit"],
                status="active"
            )
            db.add(sponsor)
            created_count += 1
            
            display_name = "Anonymous" if sponsor_info["is_anonymous"] else sponsor_info["reddit_username"]
            print(f"Created sponsor: {display_name} ({tier.name} tier, ${sponsor_info['amount']})")
        
        if created_count > 0:
            db.commit()
            print(f"Successfully created {created_count} test sponsors")
        else:
            print("No new test sponsors created")
            
    except Exception as e:
        print(f"Error creating test sponsors: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_sponsors() 