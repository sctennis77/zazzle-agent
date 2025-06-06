import os
import json
import logging
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ZazzleProductScraper:
    """Scraper for Zazzle bestseller products."""
    
    def __init__(self):
        """Initialize the scraper with configuration."""
        self.base_url = "https://www.zazzle.com"
        self.bestseller_url = f"{self.base_url}/bestsellers"
        self.scrape_delay = int(os.getenv('SCRAPE_DELAY', '2'))
        self.max_products = int(os.getenv('MAX_PRODUCTS', '100'))
        
    def scrape_products(self) -> List[Dict]:
        """Scrape bestseller products from Zazzle."""
        try:
            logger.info(f"Scraping bestseller products from {self.bestseller_url}")
            response = requests.get(self.bestseller_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            products = []
            
            # Find product elements (adjust selectors based on actual HTML structure)
            product_elements = soup.select('.product-item')[:self.max_products]
            
            for element in product_elements:
                try:
                    product_id = element.get('data-product-id', '')
                    name = element.select_one('.product-name').text.strip()
                    image_url = element.select_one('img').get('src', '')
                    
                    # Download and save screenshot
                    screenshot_path = self._save_screenshot(image_url, product_id)
                    
                    products.append({
                        'product_id': product_id,
                        'name': name,
                        'screenshot_path': screenshot_path
                    })
                    
                    logger.info(f"Scraped product: {name} ({product_id})")
                    
                except Exception as e:
                    logger.error(f"Error scraping product: {str(e)}")
                    continue
            
            return products
            
        except Exception as e:
            logger.error(f"Error scraping products: {str(e)}")
            return []
    
    def _save_screenshot(self, image_url: str, product_id: str) -> str:
        """Download and save product screenshot."""
        try:
            # Create screenshots directory if it doesn't exist
            os.makedirs('outputs/screenshots', exist_ok=True)
            
            # Download image
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Save image
            screenshot_path = f'outputs/screenshots/{product_id}.png'
            with open(screenshot_path, 'wb') as f:
                f.write(response.content)
            
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Error saving screenshot for {product_id}: {str(e)}")
            return f'outputs/screenshots/{product_id}.png'  # Return path even if download fails
    
    def save_to_config(self, products: List[Dict]):
        """Save scraped products to configuration file."""
        try:
            config = {'products': products}
            with open('app/products_config.json', 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Saved {len(products)} products to configuration")
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")

def main():
    """Main entry point for the scraper."""
    scraper = ZazzleProductScraper()
    products = scraper.scrape_products()
    scraper.save_to_config(products)

if __name__ == '__main__':
    main() 