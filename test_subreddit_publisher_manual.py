#!/usr/bin/env python3
"""
Manual test script for SubredditPublisher.

This script tests the SubredditPublisher with real database data.
Run with: python3 test_subreddit_publisher_manual.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.subreddit_publisher import SubredditPublisher
from app.db.database import init_db
from app.db.models import ProductInfo


def main():
    """Test the SubredditPublisher with real data."""
    print("🧪 Testing SubredditPublisher with real data...")
    
    # Initialize the database
    init_db()
    
    # Create publisher in dry run mode
    publisher = SubredditPublisher(dry_run=True)
    
    try:
        # Get a list of available products
        from sqlalchemy.orm import Session
        from app.db.database import SessionLocal
        
        session = SessionLocal()
        products = session.query(ProductInfo).limit(5).all()
        
        if not products:
            print("❌ No products found in database. Please run the pipeline first to generate some products.")
            return
        
        print(f"📦 Found {len(products)} products in database:")
        for i, product in enumerate(products, 1):
            print(f"  {i}. ID: {product.id}, Theme: {product.theme}, Type: {product.product_type}")
        
        # Test with the first product
        test_product_id = str(products[0].id)
        print(f"\n🎯 Testing with product ID: {test_product_id}")
        
        # Test the full publication flow
        result = publisher.publish_product(test_product_id)
        
        print(f"\n📊 Publication Result:")
        print(f"  Success: {result['success']}")
        print(f"  Product ID: {result['product_id']}")
        print(f"  Subreddit: {result['subreddit']}")
        print(f"  Dry Run: {result['dry_run']}")
        
        if result['success']:
            print(f"  Submitted Post: {result['submitted_post']}")
            print(f"  Saved Post: {result['saved_post']}")
        else:
            print(f"  Error: {result['error']}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        publisher.close()
        session.close()


if __name__ == "__main__":
    main() 