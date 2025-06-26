#!/usr/bin/env python3
"""
Script to create sponsor tiers for testing the sponsor display functionality.
"""

from app.db.database import SessionLocal
from app.db.models import SponsorTier
from decimal import Decimal

def create_sponsor_tiers():
    """Create sponsor tiers for testing."""
    db = SessionLocal()
    
    try:
        # Check if tiers already exist
        existing_tiers = db.query(SponsorTier).all()
        if existing_tiers:
            print(f"Found {len(existing_tiers)} existing sponsor tiers:")
            for tier in existing_tiers:
                print(f"  - {tier.name}: ${tier.min_amount}")
        
        # Create additional tiers if they don't exist
        tier_data = [
            {"name": "Bronze", "min_amount": Decimal("5.00"), "description": "Basic supporter tier"},
            {"name": "Gold", "min_amount": Decimal("50.00"), "description": "Premium supporter tier"},
            {"name": "Platinum", "min_amount": Decimal("100.00"), "description": "Elite supporter tier"},
        ]
        
        created_count = 0
        for tier_info in tier_data:
            existing = db.query(SponsorTier).filter_by(name=tier_info["name"]).first()
            if not existing:
                tier = SponsorTier(
                    name=tier_info["name"],
                    min_amount=tier_info["min_amount"],
                    description=tier_info["description"]
                )
                db.add(tier)
                created_count += 1
                print(f"Created {tier.name} tier with minimum amount ${tier.min_amount}")
        
        if created_count > 0:
            db.commit()
            print(f"Successfully created {created_count} new sponsor tiers")
        else:
            print("All sponsor tiers already exist")
            
    except Exception as e:
        print(f"Error creating sponsor tiers: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_sponsor_tiers() 