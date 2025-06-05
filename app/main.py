import os
import logging
import json
from typing import List, Dict

from app.affiliate_linker import ZazzleAffiliateLinker
from app.content_generator import ContentGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Zazzle Affiliate Marketing Agent")

    # Get environment variables
    zazzle_affiliate_id = os.getenv('ZAZZLE_AFFILIATE_ID')
    openai_api_key = os.getenv('OPENAI_API_KEY')

    if not zazzle_affiliate_id:
        logger.error("ZAZZLE_AFFILIATE_ID environment variable not set.")
        return
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable not set.")
        return

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
        return

    # Initialize components
    linker = ZazzleAffiliateLinker(affiliate_id=zazzle_affiliate_id)
    content_gen = ContentGenerator(api_key=openai_api_key)

    # Process products
    processed_products = []
    for product in products_data:
        product_id = product.get('product_id', 'N/A')
        product_name = product.get('name', f'Product {product_id}') # Use name from config as placeholder title

        # Add title to product dict for linker and generator compatibility
        product['title'] = product_name

        # Generate affiliate link
        affiliate_link = linker.generate_affiliate_link(product)
        product['affiliate_link'] = affiliate_link

        # Generate tweet content with error handling
        try:
            tweet_text = content_gen.generate_tweet_content(product)
            product['tweet_text'] = tweet_text
        except Exception as e:
            logger.error(f"Error generating tweet content for product {product_id}: {e}")
            product['tweet_text'] = "Error generating tweet content."

        processed_products.append(product)

    # Output results (for now, just print)
    logger.info("\n--- Processed Products ---")
    for product in processed_products:
        print(f"Product ID: {product.get('product_id','N/A')}")
        print(f"Name: {product.get('name','N/A')}")
        print(f"Affiliate Link: {product.get('affiliate_link','N/A')}")
        print(f"Tweet Content: {product.get('tweet_text','N/A')}")
        print("---")

    logger.info("Zazzle Affiliate Marketing Agent finished.")

if __name__ == "__main__":
    main() 