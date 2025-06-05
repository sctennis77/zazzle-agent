import os
import logging
import json
from typing import List, Dict
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

from app.affiliate_linker import ZazzleAffiliateLinker
from app.content_generator import ContentGenerator

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

def save_to_csv(products: List[Dict[str, str]]):
    """
    Save processed products to a CSV file.
    
    Args:
        products: List of dictionaries containing product information.
    """
    if not products:
        logger.info("No products to save to CSV.")
        return
        
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'outputs/listings_{timestamp}.csv'
    
    df = pd.DataFrame(products)
    df = df[['product_id', 'name', 'affiliate_link', 'tweet_text']] # Ensure column order
    df.to_csv(filename, index=False)
    logger.info(f"Saved {len(products)} products to {filename}")

def main():
    logger.info("Starting Zazzle Affiliate Marketing Agent")

    # Get environment variables
    zazzle_affiliate_id = os.getenv('ZAZZLE_AFFILIATE_ID')
    openai_api_key = os.getenv('OPENAI_API_KEY') # Get the key again here for the rest of the function

    if not zazzle_affiliate_id:
        logger.error("ZAZZLE_AFFILIATE_ID environment variable not set.")
        return
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set.")
        return

    # Ensure output directory exists
    ensure_output_dir()

    try:
        # Read product data from config file
        config_file = 'app/products_config.json'
        with open(config_file, 'r') as f:
            products_data = json.load(f)
        logger.info(f"Successfully loaded {len(products_data)} products from {config_file}")

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        return
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from configuration file: {config_file}")
        return
    except Exception as e:
        logger.error(f"Error reading configuration file: {e}")
        return

    if not products_data:
        logger.warning("No products found in the configuration file.")
        # Still attempt to save an empty CSV or log this outcome
        save_to_csv([]) # Save empty to indicate no data processed
        return

    # Initialize components
    linker = ZazzleAffiliateLinker(affiliate_id=zazzle_affiliate_id)
    
    # Temporarily unset proxy environment variables before initializing OpenAI client
    original_http_proxy = os.environ.pop('HTTP_PROXY', None)
    original_https_proxy = os.environ.pop('HTTPS_PROXY', None)
    original_all_proxy = os.environ.pop('ALL_PROXY', None)
    original_no_proxy = os.environ.pop('NO_PROXY', None)

    try:
        content_gen = ContentGenerator(api_key=openai_api_key)
    finally:
        # Restore original proxy environment variables
        if original_http_proxy is not None: os.environ['HTTP_PROXY'] = original_http_proxy
        if original_https_proxy is not None: os.environ['HTTPS_PROXY'] = original_https_proxy
        if original_all_proxy is not None: os.environ['ALL_PROXY'] = original_all_proxy
        if original_no_proxy is not None: os.environ['NO_PROXY'] = original_no_proxy


    # Process products
    processed_products = []
    for product in products_data:
        product_id = product.get('product_id', 'N/A')
        product_name = product.get('name', f'Product {product_id}') # Use name from config as placeholder title

        # Add title to product dict for linker and generator compatibility
        # Ensure the original product dictionary is copied or updated carefully
        current_product_data = product.copy() # Work on a copy to not modify original list during iteration if needed
        current_product_data['title'] = product_name # Add title for content generation

        # Generate affiliate link
        affiliate_link = linker.generate_affiliate_link(current_product_data)
        current_product_data['affiliate_link'] = affiliate_link

        # Generate tweet content with error handling
        try:
            tweet_text = content_gen.generate_tweet_content(current_product_data)
            current_product_data['tweet_text'] = tweet_text
        except Exception as e:
            logger.error(f"Error generating tweet content for product {product_id}: {e}")
            current_product_data['tweet_text'] = "Error generating tweet content."

        processed_products.append(current_product_data)

    # Save results to CSV
    save_to_csv(processed_products)

    # Output results (for now, also print)
    logger.info("\n--- Processed Products Summary ---")
    for product in processed_products:
        print(f"Product ID: {product.get('product_id','N/A')}")
        print(f"Name: {product.get('name','N/A')}")
        print(f"Affiliate Link: {product.get('affiliate_link','N/A')}")
        print(f"Tweet Content: {product.get('tweet_text','N/A')}")
        print("---")

    logger.info("Zazzle Affiliate Marketing Agent finished.")

if __name__ == "__main__":
    main() 