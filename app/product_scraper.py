import os
import time
import logging
from typing import List, Dict
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ZazzleProductScraper:
    def __init__(self, delay: int = 2):
        self.delay = delay
        self.base_url = "https://www.zazzle.com/bestsellers"
        self.driver = self._setup_driver()

    def _setup_driver(self) -> webdriver.Chrome:
        """Set up and return a configured Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)

    def scrape_bestsellers(self, max_products: int = 100) -> List[Dict[str, str]]:
        """
        Scrape bestseller products from Zazzle.
        Returns a list of dictionaries containing product information.
        """
        logger.info(f"Starting to scrape bestsellers from {self.base_url}")
        products = []
        
        try:
            self.driver.get(self.base_url)
            time.sleep(self.delay)  # Allow page to load
            
            # Get the page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find product elements (adjust selectors based on actual page structure)
            product_elements = soup.find_all('div', class_='product-card')
            
            for element in product_elements[:max_products]:
                try:
                    title = element.find('h3', class_='product-title').text.strip()
                    product_id = element.get('data-product-id', '')
                    
                    if title and product_id:
                        products.append({
                            'title': title,
                            'product_id': product_id
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing product: {str(e)}")
                    continue
                
                time.sleep(self.delay)
                
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
        finally:
            self.driver.quit()
            
        logger.info(f"Successfully scraped {len(products)} products")
        return products

    def scrape_category(self, category_url: str, max_products: int = 100) -> List[Dict[str, str]]:
        """
        Scrape products from a specific category page.
        Returns a list of dictionaries containing product information.
        """
        logger.info(f"Starting to scrape category: {category_url}")
        self.base_url = category_url
        return self.scrape_bestsellers(max_products) 