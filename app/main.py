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
    """Main entry point for the application."""
    # Load environment variables
    load_dotenv()

    # Initialize logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Load products from configuration
    products = load_products()

    # Get required environment variables
    zazzle_affiliate_id = os.getenv('ZAZZLE_AFFILIATE_ID')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not zazzle_affiliate_id:
        logger.error("ZAZZLE_AFFILIATE_ID environment variable not set.")
        return
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set.")
        return

    # Initialize components
    linker = ZazzleAffiliateLinker(affiliate_id=zazzle_affiliate_id)
    content_gen = ContentGenerator(api_key=openai_api_key)

    processed_products = []
    for product in products:
        logger.info(f"Processing product: {product.name}")
        try:
            # Generate affiliate link
            product.affiliate_link = linker.generate_affiliate_link(product.product_id, product.name)
            # Generate content
            product.content = content_gen.generate_content(product.name)
            product.content_type = ContentType.REDDIT
            product.identifier = Product.generate_identifier(product.product_id)
            processed_products.append(product)
        except Exception as e:
            logger.error(f"Error processing product {product.product_id}: {e}")
            continue

    # Save results to CSV
    if processed_products:
        save_to_csv(processed_products)
        logger.info("Results saved to CSV.")
    else:
        logger.warning("No products were processed successfully.")

    logger.info("Product processing completed")

if __name__ == '__main__':
    main() 