#!/usr/bin/env python3
"""
Seed script to populate sponsor tiers with initial data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from app.db.database import SessionLocal
from app.db.models import SponsorTier


def seed_sponsor_tiers():
    """Seed the sponsor_tiers table with initial data."""
    session = SessionLocal()
    
    try:
        # Check if tiers already exist
        existing_tiers = session.query(SponsorTier).count()
        if existing_tiers > 0:
            print(f"Sponsor tiers already exist ({existing_tiers} found). Skipping seed.")
            return
        
        # Define sponsor tiers
        tiers = [
            {
                "name": "Bronze Supporter",
                "min_amount": Decimal("5.00"),
                "benefits": "Name on supporter wall, 1 commission credit",
                "description": "Basic supporter tier with commission credit"
            },
            {
                "name": "Silver Supporter", 
                "min_amount": Decimal("25.00"),
                "benefits": "Name on supporter wall, 5 commission credits, priority queue",
                "description": "Mid-tier supporter with priority access"
            },
            {
                "name": "Gold Supporter",
                "min_amount": Decimal("100.00"), 
                "benefits": "Name on supporter wall, 20 commission credits, priority queue, custom requests",
                "description": "Premium supporter with custom commission options"
            },
            {
                "name": "Platinum Supporter",
                "min_amount": Decimal("500.00"),
                "benefits": "Name on supporter wall, 100 commission credits, priority queue, custom requests, exclusive content",
                "description": "Elite supporter with exclusive benefits"
            }
        ]
        
        # Create sponsor tiers
        for tier_data in tiers:
            tier = SponsorTier(**tier_data)
            session.add(tier)
        
        session.commit()
        print(f"Successfully seeded {len(tiers)} sponsor tiers:")
        for tier in tiers:
            print(f"  - {tier['name']}: ${tier['min_amount']}")
            
    except Exception as e:
        print(f"Error seeding sponsor tiers: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_sponsor_tiers() 