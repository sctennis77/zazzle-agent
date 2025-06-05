import os
import logging
import json
from typing import List, Dict
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

from app.affiliate_linker import ZazzleAffiliateLinker, ZazzleAffiliateLinkerError, InvalidProductDataError
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

def save_to_csv(products: List[Dict], force: bool = False) -> str:
    """
    Save processed products to a CSV file.
    
    Args:
        products: List of processed product dictionaries
        force: Whether to force creation of a new file
        
    Returns:
        str: Path to the saved CSV file
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'outputs/listings_{timestamp}.csv'
    
    if not force:
        # Try to find the most recent CSV file
        import glob
        csv_files = glob.glob('outputs/listings_*.csv')
        if csv_files:
            try:
                filename = max(csv_files, key=os.path.getctime)
                logger.info(f"Using existing CSV file: {filename}")
            except Exception as e:
                logger.warning(f"Error finding most recent CSV file: {e}")
    
    try:
        df = pd.DataFrame(products)
        df.to_csv(filename, index=False)
        logger.info(f"Saved {len(products)} products to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error saving to CSV: {e}")
        raise

def process_product(product: Dict, linker: ZazzleAffiliateLinker, content_gen: ContentGenerator, force_new_content: bool = False) -> Dict:
    """
    Process a single product, generating affiliate link and content.
    
    Args:
        product: Product data dictionary
        linker: ZazzleAffiliateLinker instance
        content_gen: ContentGenerator instance
        force_new_content: Whether to force generation of new content
        
    Returns:
        Dict: Processed product data
    """
    product_id = product.get('product_id', 'N/A')
    product_name = product.get('name', f'Product {product_id}')
    
    try:
        # Prepare product data for affiliate link generation
        current_product_data = product.copy()
        current_product_data['title'] = product_name
        
        # Generate affiliate link
        try:
            affiliate_link = linker.generate_affiliate_link(current_product_data)
            current_product_data['affiliate_link'] = affiliate_link
        except (InvalidProductDataError, ZazzleAffiliateLinkerError) as e:
            logger.error(f"Error generating affiliate link for product {product_id}: {e}")
            current_product_data['affiliate_link'] = "Error generating affiliate link"
        
        # Check for existing content
        existing_content = None
        if not force_new_content:
            try:
                csv_files = glob.glob('outputs/listings_*.csv')
                if csv_files:
                    latest_csv = max(csv_files, key=os.path.getctime)
                    df = pd.read_csv(latest_csv)
                    existing_row = df[df['product_id'] == product_id]
                    if not existing_row.empty:
                        existing_content = existing_row.iloc[0].to_dict()
                        logger.info(f"Found existing content for product {product_id}")
            except Exception as e:
                logger.warning(f"Error checking for existing content: {e}")
        
        # Generate or use existing content
        if existing_content and not force_new_content:
            current_product_data['tweet_text'] = existing_content['tweet_text']
            # Keep the new affiliate link if it was successfully generated
            if current_product_data['affiliate_link'] != "Error generating affiliate link":
                current_product_data['affiliate_link'] = existing_content.get('affiliate_link', current_product_data['affiliate_link'])
        else:
            try:
                tweet_text = content_gen.generate_tweet_content(current_product_data)
                current_product_data['tweet_text'] = tweet_text
            except Exception as e:
                logger.error(f"Error generating tweet content for product {product_id}: {e}")
                current_product_data['tweet_text'] = "Error generating tweet content."
        
        # Add unique identifier
        current_product_data['identifier'] = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{product_id}"
        return current_product_data
        
    except Exception as e:
        logger.error(f"Unexpected error processing product {product_id}: {e}")
        return {
            'product_id': product_id,
            'name': product_name,
            'affiliate_link': "Error processing product",
            'tweet_text': "Error processing product",
            'identifier': f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{product_id}"
        }

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

    # Process products
    processed_products = []
    for product in products_data:
        processed_product = process_product(product, linker, content_gen, force_new_content)
        processed_products.append(processed_product)

    # Save results to CSV
    try:
        save_to_csv(processed_products, force=force_new_content)
    except Exception as e:
        logger.error(f"Error saving results to CSV: {e}")
        return

    # Output results
    logger.info("\n--- Processed Products Summary ---")
    for product in processed_products:
        logger.info(f"Product ID: {product.get('product_id','N/A')}")
        logger.info(f"Name: {product.get('name','N/A')}")
        logger.info(f"Affiliate Link: {product.get('affiliate_link','N/A')}")
        logger.info(f"Tweet Content: {product.get('tweet_text','N/A')}")
        logger.info("---")

    logger.info("Zazzle Affiliate Marketing Agent finished.")

if __name__ == '__main__':
    main() 