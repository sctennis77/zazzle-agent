import os
import logging
import json
import glob
import argparse
from typing import List, Dict, Optional, Any
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
from app.utils.logging_config import setup_logging

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
    """Ensure the output directory exists."""
    output_dir = os.getenv('OUTPUT_DIR', 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'screenshots'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'images'), exist_ok=True)
    logger.info("Ensured outputs directory exists")

def save_to_csv(product_info: Dict[str, Any]):
    """Save product information to CSV file."""
    csv_file = "processed_products.csv"
    file_exists = os.path.isfile(csv_file)
    
    # Ensure all required fields are present
    required_fields = ['theme', 'text', 'color', 'quantity', 'post_title', 'post_url', 
                      'product_url', 'image_url', 'model', 'prompt_version', 'product_type', 'zazzle_template_id', 'zazzle_tracking_code', 'design_instructions']
    
    for field in required_fields:
        if field not in product_info:
            product_info[field] = ''
    
    # Filter out extra fields not in required_fields
    filtered_product_info = {k: product_info[k] for k in required_fields if k in product_info}
    
    with open(csv_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=required_fields)
        if not file_exists:
            writer.writeheader()
        writer.writerow(filtered_product_info)
    
    logger.info(f"Saved {len(filtered_product_info)} products to {csv_file}")

def log_product_info(product_info: Dict[str, Any]):
    """Log product information in a readable format."""
    logger.info("\nGenerated Product Info:")
    logger.info(f"Theme: {product_info.get('theme', '')}")
    logger.info(f"Text: {product_info.get('text', '')}")
    logger.info(f"Color: {product_info.get('color', '')}")
    logger.info(f"Quantity: {product_info.get('quantity', '')}")
    logger.info(f"Model: {product_info.get('model', '')}")
    logger.info(f"Prompt Version: {product_info.get('prompt_version', '')}")
    
    logger.info("\nReddit Context:")
    logger.info(f"Post Title: {product_info.get('post_title', '')}")
    logger.info(f"Post URL: {product_info.get('post_url', '')}")
    
    logger.info("\nProduct URL:")
    logger.info("To view and customize the product, open this URL in your browser:")
    logger.info(f"{product_info.get('product_url', '')}")
    
    logger.info("\nGenerated Image URL:")
    logger.info(f"{product_info.get('image_url', '')}")

async def run_full_pipeline(model: str = "dall-e-2"):
    """Run the full pipeline: find post, generate image, create product."""
    try:
        # Initialize RedditAgent with the specified model
        reddit_agent = RedditAgent(model=model)
        
        # Find a post and create a product
        product_info = await reddit_agent.find_and_create_product()
        
        if product_info:
            # Get prompt info from the image generator
            prompt_info = reddit_agent.image_generator.get_prompt_info()
            
            # Add model and version info to the product info
            product_info.update({
                'model': model,
                'prompt_version': prompt_info['version']
            })
            
            # Save to CSV
            save_to_csv(product_info)
            
            # Log the results
            log_product_info(product_info)
            
            return product_info
        else:
            logger.warning("No suitable post found for product creation")
            return None
            
    except Exception as e:
        logger.error(f"Error in full pipeline: {str(e)}")
        raise

async def run_generate_image_pipeline(image_prompt: str, model: str = "dall-e-2"):
    """Run the image generation pipeline with a given prompt."""
    image_generator = ImageGenerator(model=model)
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
    parser = argparse.ArgumentParser(description='Run the Reddit-to-Zazzle dynamic product flow.')
    parser.add_argument('--mode', type=str, default='full',
                      choices=['full', 'image', 'test-vote', 'test-comment', 'test-engaging', 'test-marketing'],
                      help='Operation mode')
    parser.add_argument('--prompt', type=str, help='Image generation prompt (required for image mode)')
    parser.add_argument('--model', type=str, default='dall-e-2',
                      choices=['dall-e-2', 'dall-e-3'],
                      help='DALL-E model to use for image generation')
    args = parser.parse_args()

    if args.mode == 'image' and not args.prompt:
        parser.error("--prompt is required for image mode")

    ensure_output_dir()

    if args.mode == 'full':
        await run_full_pipeline(model=args.model)
    elif args.mode == 'image':
        await run_generate_image_pipeline(args.prompt, args.model)
    elif args.mode == 'test-vote':
        await test_reddit_voting()
    elif args.mode == 'test-comment':
        await test_reddit_post_comment()
    elif args.mode == 'test-engaging':
        await test_reddit_engaging_comment()
    elif args.mode == 'test-marketing':
        await test_reddit_marketing_comment()

if __name__ == '__main__':
    asyncio.run(main()) 