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
import asyncio

from app.affiliate_linker import ZazzleAffiliateLinker, ZazzleAffiliateLinkerError, InvalidProductDataError
from app.content_generator import ContentGenerator
from app.models import Product, ContentType
from app.agents.reddit_agent import RedditAgent
from app.zazzle_templates import get_product_template, ZAZZLE_STICKER_TEMPLATE
from app.image_generator import ImageGenerator

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
                'created_at',
                'has_reddit_context'
            ])
            writer.writeheader()
            
            for product in products:
                # Support both dict and Product object
                if hasattr(product, 'to_dict'):
                    product_dict = product.to_dict()
                    product_url = product_dict.get('affiliate_link', '')
                    text_content = product_dict.get('content', '')
                    image_url = product_dict.get('screenshot_path', '') # Assuming screenshot_path can be image_url
                else:
                    product_dict = product
                    product_url = product_dict.get('product_url', '')
                    text_content = product_dict.get('text', '')
                    image_url = product_dict.get('image_url', '')

                reddit_context = product_dict.get('reddit_context', {})
                has_reddit_context = bool(reddit_context and reddit_context.get('id'))
                
                writer.writerow({
                    'product_url': product_url,
                    'text_content': text_content,
                    'image_url': image_url,
                    'reddit_post_id': reddit_context.get('id', ''),
                    'reddit_post_title': reddit_context.get('title', ''),
                    'reddit_post_url': reddit_context.get('url', ''),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'has_reddit_context': has_reddit_context
                })
        
        logger.info(f"Saved {len(products)} products to {filename}")
    except Exception as e:
        logger.error(f"Error saving to CSV: {str(e)}")
        raise

async def run_full_pipeline():
    """Run the complete Reddit-to-Zazzle dynamic product flow."""
    products = []
    reddit_agent = RedditAgent()
    product_info = await reddit_agent.find_and_create_product()
    if product_info:
        products.append(product_info)
        save_to_csv(products, "processed_products.csv")
        logger.info("\nGenerated Product Info:")
        logger.info(f"Theme: {product_info.get('theme', 'default')}")
        logger.info(f"Text: {product_info.get('text', '')}")
        logger.info(f"Color: {product_info.get('color', 'Blue')}")
        logger.info(f"Quantity: {product_info.get('quantity', 12)}")
        
        reddit_context = product_info.get('reddit_context', {})
        if reddit_context and reddit_context.get('id'):
            logger.info("\nReddit Context:")
            logger.info(f"Post Title: {reddit_context.get('title', '')}")
            logger.info(f"Post URL: {reddit_context.get('url', '')}")
        else:
            logger.info("\nNote: This product was created without a Reddit post context.")
        
        logger.info("\nProduct URL:")
        logger.info("To view and customize the product, open this URL in your browser:")
        logger.info(product_info.get('product_url', ''))

        # Print image URL if available
        if product_info.get('image'):
            logger.info("\nGenerated Image URL:")
            logger.info(product_info.get('image'))
        if product_info.get('image_local_path'):
            logger.info("Generated Image Local Path:")
            logger.info(product_info.get('image_local_path'))

    else:
        logger.warning("No product was generated.")

async def run_generate_image_pipeline(image_prompt: str):
    """Run the image generation pipeline with a given prompt."""
    image_generator = ImageGenerator()
    try:
        imgur_url, local_path = await image_generator.generate_image(image_prompt)
        logger.info(f"\nGenerated Image URL: {imgur_url}")
        logger.info(f"Generated Image Local Path: {local_path}")
    except Exception as e:
        logger.error(f"Error generating image: {e}")

async def test_reddit_voting():
    """Test the Reddit agent's upvoting/downvoting behavior without posting affiliate material."""
    reddit_agent = RedditAgent()
    
    # Get a trending post from r/golf
    subreddit = reddit_agent.reddit.subreddit("golf")
    trending_post = next(subreddit.hot(limit=1), None)
    
    if trending_post:
        logger.info("\nFound trending post:")
        logger.info(f"Title: {trending_post.title}")
        logger.info(f"URL: https://reddit.com{trending_post.permalink}")
        
        # Interact with the post
        action = reddit_agent.interact_with_votes(trending_post.id)
        logger.info(f"\nAction taken: {action}")
    else:
        logger.info("No trending post found in r/golf.")

async def test_reddit_comment_voting():
    """Test the Reddit agent's comment upvoting/downvoting behavior without posting affiliate material."""
    reddit_agent = RedditAgent()
    
    # Get a trending post from r/golf
    subreddit = reddit_agent.reddit.subreddit("golf")
    trending_post = next(subreddit.hot(limit=1), None)
    
    if trending_post:
        logger.info("\nFound trending post:")
        logger.info(f"Title: {trending_post.title}")
        logger.info(f"URL: https://reddit.com{trending_post.permalink}")
        
        # Get top-level comments
        trending_post.comments.replace_more(limit=0)  # Load top-level comments only
        for comment in trending_post.comments.list():
            if not comment.stickied:  # Skip stickied comments
                logger.info(f"\nFound comment:")
                logger.info(f"Text: {comment.body}")
                logger.info(f"Author: u/{comment.author}")
                
                # Interact with the comment
                action = reddit_agent.interact_with_votes(trending_post.id, comment.id)
                logger.info(f"\nAction taken: {action}")
                break  # Process only one comment for testing
    else:
        logger.info("No trending post found in r/golf.")

async def test_reddit_post_comment():
    """Test the Reddit agent's ability to comment on posts without actually posting."""
    reddit_agent = RedditAgent()
    
    # Get a trending post from r/golf
    subreddit = reddit_agent.reddit.subreddit("golf")
    trending_post = next(subreddit.hot(limit=1), None)
    
    if trending_post:
        logger.info("\nFound trending post:")
        logger.info(f"Title: {trending_post.title}")
        logger.info(f"URL: https://reddit.com{trending_post.permalink}")
        
        # Generate a test comment
        test_comment = "This is a test comment that would be posted in reply to the post."
        
        # Attempt to comment on the post
        action = reddit_agent.comment_on_post(trending_post.id, test_comment)
        if action:
            logger.info("\nProposed action:")
            logger.info(f"Type: {action['type']}")
            logger.info(f"Post: {action['post_title']}")
            logger.info(f"Post URL: {action['post_link']}")
            logger.info(f"Comment text: {action['comment_text']}")
            logger.info(f"Action: {action['action']}")
    else:
        logger.info("No trending post found in r/golf.")

async def test_reddit_engaging_comment():
    """Test the Reddit agent's ability to generate engaging comments based on post context."""
    reddit_agent = RedditAgent()
    
    # Get a trending post from r/golf
    subreddit = reddit_agent.reddit.subreddit("golf")
    trending_post = next(subreddit.hot(limit=1), None)
    
    if trending_post:
        logger.info("\nFound trending post:")
        logger.info(f"Title: {trending_post.title}")
        logger.info(f"URL: https://reddit.com{trending_post.permalink}")
        
        # Analyze post context
        post_context = reddit_agent._analyze_post_context(trending_post)
        
        # Generate engaging comment
        engaging_comment = reddit_agent._generate_engaging_comment(post_context)
        
        if engaging_comment:
            logger.info("\nEngaging Comment:")
            logger.info(engaging_comment)
        else:
            logger.info("No engaging comment generated.")
    else:
        logger.info("No trending post found in r/golf.")

async def test_reddit_marketing_comment():
    """Test the Reddit agent's ability to generate marketing comments based on post context and product."""
    reddit_agent = RedditAgent()
    
    # Mock a product for testing
    mock_product = Product(
        product_id="mock_product_id",
        name="Cool Golf Sticker",
        description="A cool sticker for golf enthusiasts",
        content="This is a mock content for the sticker.",
        affiliate_link="https://example.com/mock_sticker"
    )
    
    # Get a trending post from r/golf
    subreddit = reddit_agent.reddit.subreddit("golf")
    trending_post = next(subreddit.hot(limit=1), None)
    
    if trending_post:
        logger.info("\nFound trending post:")
        logger.info(f"Title: {trending_post.title}")
        logger.info(f"URL: https://reddit.com{trending_post.permalink}")
        
        # Analyze post context
        post_context = reddit_agent._analyze_post_context(trending_post)
        
        # Generate marketing comment
        marketing_comment = reddit_agent._generate_marketing_comment(mock_product, post_context)
        
        if marketing_comment:
            logger.info("\nMarketing Comment:")
            logger.info(marketing_comment)
        else:
            logger.info("No marketing comment generated.")
    else:
        logger.info("No trending post found in r/golf.")

async def test_reddit_comment_marketing_reply():
    """Test the Reddit agent's ability to reply to a comment with marketing content."""
    reddit_agent = RedditAgent()
    
    # Mock a product for testing
    mock_product = Product(
        product_id="mock_product_id",
        name="Awesome Golf Tool",
        description="A must-have tool for every golfer.",
        content="This is a mock content for the golf tool.",
        affiliate_link="https://example.com/mock_golf_tool"
    )

    # Get a trending post from r/golf
    subreddit = reddit_agent.reddit.subreddit("golf")
    trending_post = next(subreddit.hot(limit=1), None)

    if trending_post:
        logger.info("\nFound trending post:")
        logger.info(f"Title: {trending_post.title}")
        logger.info(f"URL: https://reddit.com{trending_post.permalink}")

        # Get top-level comments
        trending_post.comments.replace_more(limit=0)  # Load top-level comments only
        for comment in trending_post.comments.list():
            if not comment.stickied:  # Skip stickied comments
                logger.info(f"\nFound comment to reply to:")
                logger.info(f"Text: {comment.body}")
                logger.info(f"Author: u/{comment.author}")

                # Analyze post context
                post_context = reddit_agent._analyze_post_context(trending_post)

                # Reply to the comment with marketing content
                action = reddit_agent.reply_to_comment_with_marketing(comment.id, mock_product, post_context)
                if action:
                    logger.info("\nProposed action:")
                    logger.info(f"Type: {action['type']}")
                    logger.info(f"Comment ID: {action['comment_id']}")
                    logger.info(f"Reply text: {action['reply_text']}")
                    logger.info(f"Action: {action['action']}")
                break  # Process only one comment for testing
    else:
        logger.info("No trending post found in r/golf.")

async def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description='Zazzle Agent')
    parser.add_argument('--mode', type=str, default='full',
                      choices=['full', 'test-voting', 'test-voting-comment', 
                              'test-post-comment', 'test-engaging-comment',
                              'test-marketing-comment', 'test-marketing-comment-reply'],
                      help='Operation mode')
    args = parser.parse_args()

    if args.mode == 'full':
        await run_full_pipeline()
    elif args.mode == 'test-voting':
        await test_reddit_voting()
    elif args.mode == 'test-voting-comment':
        await test_reddit_comment_voting()
    elif args.mode == 'test-post-comment':
        await test_reddit_post_comment()
    elif args.mode == 'test-engaging-comment':
        await test_reddit_engaging_comment()
    elif args.mode == 'test-marketing-comment':
        await test_reddit_marketing_comment()
    elif args.mode == 'test-marketing-comment-reply':
        await test_reddit_comment_marketing_reply()

if __name__ == '__main__':
    asyncio.run(main()) 