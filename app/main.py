import os
import logging
import json
import glob
from typing import List, Dict, Optional
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

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

def save_to_csv(products: List[Product], output_dir: str = "outputs") -> str:
    """Save processed products to a CSV file."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"listings_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        data = [product.to_dict() for product in products]
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
        logger.info(f"Saved {len(products)} products to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error saving to CSV: {str(e)}")
        raise

def main():
    """Main entry point for the Zazzle Affiliate Marketing Agent."""
    logger.info("Starting Zazzle Affiliate Marketing Agent")

    # Get environment variables
    zazzle_affiliate_id = os.getenv('ZAZZLE_AFFILIATE_ID')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    force_new_content = os.getenv('FORCE_NEW_CONTENT', 'false').lower() == 'true'

    if not zazzle_affiliate_id:
        logger.error("ZAZZLE_AFFILIATE_ID environment variable not set.")
        return
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set.")
        return

    # Ensure output directory exists
    ensure_output_dir()

    # Load products from config
    products = load_products()

    if not products:
        logger.warning("No products found in the configuration file.")
        save_to_csv([])
        return

    # Initialize components
    try:
        linker = ZazzleAffiliateLinker(affiliate_id=zazzle_affiliate_id)
    except ValueError as e:
        logger.error(f"Error initializing ZazzleAffiliateLinker: {e}")
        return

    # Temporarily unset proxy environment variables before initializing OpenAI client
    original_http_proxy = os.environ.pop('HTTP_PROXY', None)
    original_https_proxy = os.environ.pop('HTTPS_PROXY', None)
    original_all_proxy = os.environ.pop('ALL_PROXY', None)
    original_no_proxy = os.environ.pop('NO_PROXY', None)

    try:
        content_gen = ContentGenerator(api_key=openai_api_key)
    except Exception as e:
        logger.error(f"Error initializing ContentGenerator: {e}")
        return
    finally:
        # Restore original proxy environment variables
        if original_http_proxy is not None: os.environ['HTTP_PROXY'] = original_http_proxy
        if original_https_proxy is not None: os.environ['HTTPS_PROXY'] = original_https_proxy
        if original_all_proxy is not None: os.environ['ALL_PROXY'] = original_all_proxy
        if original_no_proxy is not None: os.environ['NO_PROXY'] = original_no_proxy

    # Initialize RedditAgent (can extend to other channels later)
    reddit_agent = RedditAgent()

    # Process each product
    processed_products = []
    for product in products:
        try:
            # Generate affiliate link
            product.affiliate_link = linker.generate_affiliate_link(product.product_id, product.name)
            # Generate content for Reddit (simulate persona)
            product.content = content_gen.generate_content(product.name)
            product.content_type = ContentType.REDDIT
            product.identifier = Product.generate_identifier(product.product_id)
            # Post as a user and interact
            reddit_agent.post_content(product, product.content)
            reddit_agent.interact_with_users(product)
            processed_products.append(product)
        except Exception as e:
            logger.error(f"Error processing product {product.product_id}: {e}")

    # Save results to CSV
    try:
        save_to_csv(processed_products)
        logger.info("Results saved to CSV.")
    except Exception as e:
        logger.error(f"Failed to save results to CSV: {str(e)}")

    # Log summary
    logger.info("\n--- Processed Products Summary ---")
    for product in processed_products:
        logger.info(f"Product ID: {product.product_id}")
        logger.info(f"Name: {product.name}")
        logger.info(f"Affiliate Link: {product.affiliate_link}")
        logger.info(f"Content Type: {product.content_type.value if product.content_type else 'None'}")
        logger.info(f"Content: {product.content}")
        logger.info("---")

    logger.info("Zazzle Affiliate Marketing Agent finished.")

if __name__ == '__main__':
    main() 