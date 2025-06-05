import os
import logging
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from app.product_scraper import ZazzleProductScraper
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

def ensure_output_dir():
    """Ensure the outputs directory exists."""
    os.makedirs('outputs', exist_ok=True)

def save_to_csv(products: list):
    """Save processed products to a CSV file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'outputs/listings_{timestamp}.csv'
    
    df = pd.DataFrame(products)
    df.to_csv(filename, index=False)
    logger.info(f"Saved {len(products)} products to {filename}")

def main():
    try:
        # Initialize components
        scraper = ZazzleProductScraper(delay=int(os.getenv('SCRAPE_DELAY', 2)))
        linker = ZazzleAffiliateLinker(affiliate_id=os.getenv('ZAZZLE_AFFILIATE_ID'))
        content_gen = ContentGenerator()
        
        # Ensure output directory exists
        ensure_output_dir()
        
        # Scrape products
        max_products = int(os.getenv('MAX_PRODUCTS', 100))
        logger.info(f"Starting to scrape up to {max_products} products")
        products = scraper.scrape_bestsellers(max_products=max_products)
        
        if not products:
            logger.error("No products were scraped")
            return
        
        # Generate affiliate links
        logger.info("Generating affiliate links")
        products = linker.generate_links_batch(products)
        
        # Generate tweet content
        logger.info("Generating tweet content")
        products = content_gen.generate_tweets_batch(products)
        
        # Save results
        save_to_csv(products)
        
        logger.info("Process completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        raise

if __name__ == "__main__":
    main() 