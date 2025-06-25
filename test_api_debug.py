#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.db.models import ProductInfo, RedditPost

def test_post_id_lookup():
    db = SessionLocal()
    try:
        # Test 1: Find RedditPost by post_id
        print("=== Testing RedditPost lookup by post_id ===")
        reddit_post = db.query(RedditPost).filter(RedditPost.post_id == "1juzYyg").first()
        if reddit_post:
            print(f"Found RedditPost: ID={reddit_post.id}, post_id={reddit_post.post_id}, subreddit={reddit_post.subreddit}")
        else:
            print("RedditPost not found by post_id '1juzYyg'")
            
        # Test 2: Find all RedditPosts
        print("\n=== All RedditPosts ===")
        all_posts = db.query(RedditPost).all()
        for post in all_posts:
            print(f"ID={post.id}, post_id={post.post_id}, subreddit={post.subreddit}")
            
        # Test 3: Find ProductInfo by RedditPost
        if reddit_post:
            print(f"\n=== ProductInfo for RedditPost ID {reddit_post.id} ===")
            product = db.query(ProductInfo).filter(ProductInfo.reddit_post_id == reddit_post.id).first()
            if product:
                print(f"Found ProductInfo: ID={product.id}, theme={product.theme}, image_url={product.image_url}")
            else:
                print("No ProductInfo found for this RedditPost")
                
        # Test 4: Test the join query
        print("\n=== Testing join query ===")
        product = db.query(ProductInfo).join(RedditPost, ProductInfo.reddit_post_id == RedditPost.id).filter(RedditPost.post_id == "1juzYyg").first()
        if product:
            print(f"Join query found product: ID={product.id}, theme={product.theme}")
        else:
            print("Join query failed to find product")
            
        # Test 5: Alternative approach - find by image_url
        print("\n=== Testing by image_url ===")
        product = db.query(ProductInfo).filter(ProductInfo.image_url.contains("1juzYyg")).first()
        if product:
            print(f"Found by image_url: ID={product.id}, theme={product.theme}")
            reddit_post = db.query(RedditPost).filter_by(id=product.reddit_post_id).first()
            if reddit_post:
                print(f"Associated RedditPost: post_id={reddit_post.post_id}, subreddit={reddit_post.subreddit}")
        else:
            print("Not found by image_url")
            
        # Test 6: Test with correct post_id
        print("\n=== Testing with correct post_id '1lizjje' ===")
        reddit_post = db.query(RedditPost).filter(RedditPost.post_id == "1lizjje").first()
        if reddit_post:
            print(f"Found RedditPost: ID={reddit_post.id}, post_id={reddit_post.post_id}, subreddit={reddit_post.subreddit}")
            
            # Test join query with correct post_id
            product = db.query(ProductInfo).join(RedditPost, ProductInfo.reddit_post_id == RedditPost.id).filter(RedditPost.post_id == "1lizjje").first()
            if product:
                print(f"Join query found product: ID={product.id}, theme={product.theme}")
            else:
                print("Join query failed to find product")
                
            # Test direct lookup
            product = db.query(ProductInfo).filter(ProductInfo.reddit_post_id == reddit_post.id).first()
            if product:
                print(f"Direct lookup found product: ID={product.id}, theme={product.theme}")
            else:
                print("Direct lookup failed to find product")
        else:
            print("RedditPost not found by post_id '1lizjje'")
            
    finally:
        db.close()

def test_by_post_id_query():
    db = SessionLocal()
    try:
        print("=== Testing the exact query from the API endpoint ===")
        
        # Test with the post_id that should exist
        post_id = "1lizjje"
        
        # This is the exact query from the API endpoint
        product = db.query(ProductInfo).join(
            RedditPost, 
            ProductInfo.reddit_post_id == RedditPost.id
        ).filter(
            RedditPost.post_id == post_id
        ).first()
        
        if product:
            print(f"✅ SUCCESS: Found product with ID {product.id}")
            print(f"   - ProductInfo.reddit_post_id: {product.reddit_post_id}")
            print(f"   - ProductInfo.pipeline_run_id: {product.pipeline_run_id}")
            print(f"   - ProductInfo.theme: {product.theme}")
        else:
            print(f"❌ FAILED: No product found for post_id '{post_id}'")
            
            # Let's debug what's in the database
            print("\n=== Debugging database contents ===")
            
            # Check if RedditPost exists
            reddit_post = db.query(RedditPost).filter(RedditPost.post_id == post_id).first()
            if reddit_post:
                print(f"✅ RedditPost exists: ID={reddit_post.id}, post_id={reddit_post.post_id}")
                
                # Check if ProductInfo exists for this RedditPost
                product_info = db.query(ProductInfo).filter(
                    ProductInfo.reddit_post_id == reddit_post.id
                ).first()
                
                if product_info:
                    print(f"✅ ProductInfo exists: ID={product_info.id}, reddit_post_id={product_info.reddit_post_id}")
                else:
                    print(f"❌ No ProductInfo found for RedditPost ID {reddit_post.id}")
            else:
                print(f"❌ RedditPost with post_id '{post_id}' not found")
                
                # Show all RedditPost entries
                print("\nAll RedditPost entries:")
                all_posts = db.query(RedditPost).all()
                for post in all_posts:
                    print(f"  - ID: {post.id}, post_id: '{post.post_id}', subreddit: {post.subreddit}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_post_id_lookup()
    test_by_post_id_query() 