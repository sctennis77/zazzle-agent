import os
import logging
import json
import glob
import argparse
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
import csv

from app.affiliate_linker import ZazzleAffiliateLinker, ZazzleAffiliateLinkerError, InvalidProductDataError
from app.content_generator import ContentGenerator
from app.models import Product, ContentType
from app.agents.reddit_agent import RedditAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Log the loaded API key (masked)
openai_api_key_loaded = os.getenv('OPENAI_API_KEY')
if openai_api_key_loaded:
    logger.info(f"OPENAI_API_KEY loaded: {openai_api_key_loaded[:5]}...{openai_api_key_loaded[-5:]}")
else:
    logger.warning("OPENAI_API_KEY not loaded.")

def ensure_output_dir():
    """Ensure the outputs directory exists."""
    os.makedirs('outputs', exist_ok=True)

def load_products(config_path: str = "app/products_config.json") -> List[Product]:
    """Load products from configuration file.
    
    Args:
        config_path: Path to the products configuration file
        
    Returns:
        List[Product]: List of Product objects
    """
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
            products_data = config_data.get('products', [])
            
        products = []
        for product_data in products_data:
            product = Product(
                product_id=product_data['product_id'],
                name=product_data['name'],
                screenshot_path=product_data.get('screenshot_path')  # Get screenshot path from config
            )
            products.append(product)
            
        logger.info(f"Loaded {len(products)} products from {config_path}")
        return products
        
    except Exception as e:
        logger.error(f"Error loading products from {config_path}: {str(e)}")
        raise

def save_to_csv(products: List, filename: str):
    """Save products to a CSV file with detailed information."""
    try:
        os.makedirs('outputs', exist_ok=True)
        with open(f'outputs/{filename}', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'product_url',
                'text_content',
                'image_url',
                'reddit_post_id',
                'reddit_post_title',
                'reddit_post_url',
                'created_at'
            ])
            writer.writeheader()
            
            for product in products:
                # Support both dict and Product object
                if hasattr(product, 'to_dict'):
                    product = product.to_dict()
                reddit_context = product.get('reddit_context', {})
                writer.writerow({
                    'product_url': product.get('product_url', ''),
                    'text_content': product.get('text', ''),
                    'image_url': product.get('image_url', ''),
                    'reddit_post_id': reddit_context.get('id', ''),
                    'reddit_post_title': reddit_context.get('title', ''),
                    'reddit_post_url': reddit_context.get('url', ''),
                    'created_at': datetime.now(timezone.utc).isoformat()
                })
        
        logger.info(f"Saved {len(products)} products to {filename}")
    except Exception as e:
        logger.error(f"Error saving to CSV: {str(e)}")
        raise

def run_full_pipeline():
    """Run the complete Reddit-to-Zazzle dynamic product flow."""
    products = []
    reddit_agent = RedditAgent()
    product_info = reddit_agent.find_and_create_product()
    if product_info:
        products.append(product_info)
        save_to_csv(products, "processed_products.csv")
        print("\nGenerated Product Info:")
        print(f"Theme: {product_info.get('theme', 'default')}")
        print(f"Text: {product_info.get('text', '')}")
        print(f"Color: {product_info.get('color', 'Blue')}")
        print(f"Quantity: {product_info.get('quantity', 12)}")
        print("\nReddit Context:")
        reddit_context = product_info.get('reddit_context', {})
        print(f"Post Title: {reddit_context.get('title', '')}")
        print(f"Post URL: {reddit_context.get('url', '')}")
        print("\nProduct URL:")
        print(f"To view and customize the product, open this URL in your browser:")
        print(product_info.get('product_url', ''))
    else:
        print("No product was generated.")

def test_reddit_voting():
    """Test the Reddit agent's upvoting/downvoting behavior without posting affiliate material."""
    reddit_agent = RedditAgent()
    
    # Get a trending post from r/golf
    subreddit = reddit_agent.reddit.subreddit("golf")
    trending_post = next(subreddit.hot(limit=1), None)
    
    if trending_post:
        print("\nFound trending post:")
        print(f"Title: {trending_post.title}")
        print(f"URL: https://reddit.com{trending_post.permalink}")
        
        # Interact with the post
        action = reddit_agent.interact_with_votes(trending_post.id)
        print(f"\nAction taken: {action}")
    else:
        print("No trending post found in r/golf.")

def test_reddit_comment_voting():
    """Test the Reddit agent's comment upvoting/downvoting behavior without posting affiliate material."""
    reddit_agent = RedditAgent()
    
    # Get a trending post from r/golf
    subreddit = reddit_agent.reddit.subreddit("golf")
    trending_post = next(subreddit.hot(limit=1), None)
    
    if trending_post:
        print("\nFound trending post:")
        print(f"Title: {trending_post.title}")
        print(f"URL: https://reddit.com{trending_post.permalink}")
        
        # Get top-level comments
        trending_post.comments.replace_more(limit=0)  # Load top-level comments only
        for comment in trending_post.comments.list():
            if not comment.stickied:  # Skip stickied comments
                print(f"\nFound comment:")
                print(f"Text: {comment.body}")
                print(f"Author: u/{comment.author}")
                
                # Interact with the comment
                action = reddit_agent.interact_with_votes(trending_post.id, comment.id)
                print(f"\nAction taken: {action}")
                break  # Process only one comment for testing
    else:
        print("No trending post found in r/golf.")

def main():
    """Main entry point with command line argument support."""
    parser = argparse.ArgumentParser(description='Zazzle Dynamic Product Generator')
    parser.add_argument('mode', choices=['full', 'test-voting', 'test-voting-comment'],
                      help='Mode to run: "full" for complete pipeline, "test-voting" for Reddit voting test, "test-voting-comment" for Reddit comment voting test')
    
    args = parser.parse_args()
    
    if args.mode == 'full':
        run_full_pipeline()
    elif args.mode == 'test-voting':
        test_reddit_voting()
    elif args.mode == 'test-voting-comment':
        test_reddit_comment_voting()

if __name__ == "__main__":
    main() 