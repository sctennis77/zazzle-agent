#!/usr/bin/env python3
"""
Test script to verify the redirect functionality works with existing products.
"""

import requests
import json
from app.db.database import get_db
from app.db.models import ProductInfo, RedditPost

def test_redirect_functionality():
    """Test the redirect functionality with existing products."""
    print("Testing redirect functionality...")
    
    # Get a sample product from the database
    db = next(get_db())
    try:
        products = db.query(ProductInfo).limit(3).all()
        
        if not products:
            print("No products found in database.")
            return False
        
        print(f"Found {len(products)} products. Testing redirect functionality...")
        
        # Test the API endpoints
        base_url = "http://localhost:8000"
        
        for i, product in enumerate(products):
            print(f"\n--- Testing Product {i+1} ---")
            
            # Extract filename from image_url
            if product.image_url:
                # Try to extract filename from the URL
                image_filename = product.image_url.split('/')[-1] if '/' in product.image_url else product.image_url
                print(f"Image filename: {image_filename}")
                
                # Test the redirect endpoint
                try:
                    redirect_url = f"{base_url}/redirect/{image_filename}"
                    print(f"Testing redirect: {redirect_url}")
                    
                    response = requests.get(redirect_url, allow_redirects=False)
                    print(f"Redirect status: {response.status_code}")
                    
                    if response.status_code == 302:
                        print(f"✅ Redirect successful! Location: {response.headers.get('Location')}")
                    else:
                        print(f"❌ Redirect failed with status: {response.status_code}")
                        if response.status_code == 404:
                            print("   This might be because the image filename doesn't match the database.")
                
                except requests.exceptions.ConnectionError:
                    print("❌ Could not connect to API server. Make sure it's running on localhost:8000")
                    return False
                except Exception as e:
                    print(f"❌ Error testing redirect: {e}")
                
                # Test the single product API endpoint
                try:
                    product_url = f"{base_url}/api/product/{image_filename}"
                    print(f"Testing product API: {product_url}")
                    
                    response = requests.get(product_url)
                    print(f"Product API status: {response.status_code}")
                    
                    if response.status_code == 200:
                        product_data = response.json()
                        print(f"✅ Product API successful!")
                        print(f"   Theme: {product_data['product_info']['theme']}")
                        print(f"   Subreddit: {product_data['reddit_post']['subreddit']}")
                        print(f"   Image URL: {product_data['product_info']['image_url']}")
                    else:
                        print(f"❌ Product API failed with status: {response.status_code}")
                        if response.status_code == 404:
                            print("   This might be because the image filename doesn't match the database.")
                
                except Exception as e:
                    print(f"❌ Error testing product API: {e}")
                
            else:
                print("⚠️  No image_url for this product")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing redirect functionality: {e}")
        return False
    finally:
        db.close()

def show_example_routes():
    """Show example routes that would work with the current setup."""
    print("\n" + "="*50)
    print("EXAMPLE ROUTES")
    print("="*50)
    
    db = next(get_db())
    try:
        products = db.query(ProductInfo).limit(2).all()
        
        for i, product in enumerate(products):
            if product.image_url:
                # Extract filename
                image_filename = product.image_url.split('/')[-1] if '/' in product.image_url else product.image_url
                safe_filename = image_filename.replace('.png', '').replace('.jpeg', '').replace('.jpg', '')
                
                # Get subreddit
                reddit_post = db.query(RedditPost).filter_by(id=product.reddit_post_id).first()
                subreddit = reddit_post.subreddit if reddit_post else "unknown"
                
                print(f"\nProduct {i+1}:")
                print(f"  Redirect URL: http://localhost:8000/redirect/{image_filename}")
                print(f"  Frontend URL: http://localhost:5173/r/{subreddit}/{safe_filename}")
                print(f"  API URL: http://localhost:8000/api/product/{image_filename}")
                print(f"  Theme: {product.theme}")
                print(f"  Subreddit: {subreddit}")
    
    except Exception as e:
        print(f"Error showing example routes: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Testing QR Code Redirect Functionality")
    print("="*50)
    
    success = test_redirect_functionality()
    
    if success:
        print("\n✅ Redirect functionality test completed!")
        show_example_routes()
    else:
        print("\n❌ Some tests failed. Check the output above.") 