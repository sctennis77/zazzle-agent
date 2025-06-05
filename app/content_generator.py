import os
import json
import logging
from typing import List, Dict, Optional
import httpx
from openai import OpenAI
from dotenv import load_dotenv
from app.models import Product

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentGenerator:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OpenAI API key cannot be empty")
        self.client = OpenAI(api_key=api_key)
        logger.info("Initializing ContentGenerator")

    def generate_tweet_content(self, product_name: str, force_new_content: bool = False) -> str:
        """Generate tweet content for a product name."""
        try:
            prompt = f"Create a tweet for the product: {product_name}"
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            tweet_text = response.choices[0].message.content.strip()
            logger.info(f"Successfully generated tweet for {product_name}")
            return tweet_text
        except Exception as e:
            logger.error(f"Error generating tweet content for {product_name}: {e}")
            return "Error generating tweet content"

    def generate_content_batch(self, products: List[Product], force_new_content: bool = False) -> List[Product]:
        processed_products = []
        for product in products:
            try:
                tweet_text = self.generate_tweet_content(product.name, force_new_content)
                product.tweet_text = tweet_text
                processed_products.append(product)
            except Exception as e:
                logger.error(f"Error processing product {product.product_id}: {e}")
        return processed_products

def generate_content_from_config(config_file: str = 'app/products_config.json'):
    """
    Reads product data from a config file and generates content for each.
    
    Args:
        config_file: Path to the JSON configuration file.
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        return

    generator = ContentGenerator(api_key=openai_api_key)

    try:
        with open(config_file, 'r') as f:
            products_data = json.load(f)
        logger.info(f"Successfully loaded product data from {config_file}")

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        return
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from configuration file: {config_file}")
        return
    except Exception as e:
        logger.error(f"Error reading configuration file: {e}")
        return

    generated_content = {}
    for product in products_data:
        # For content generation, we mainly need the title. We can fetch it if not in config,
        # or ideally, update the config with more details later.
        # For now, we'll use the 'name' from config as a placeholder for title if 'title' is missing.
        product_details = {
            'title': product.get('name', f"Product ID: {product.get('product_id', 'N/A')}"),
            'product_id': product.get('product_id', 'N/A')
        }
        tweet = generator.generate_tweet_content(product_details['title'])
        generated_content[product.get('product_id', 'N/A')] = tweet
        print(f"Product ID: {product.get('product_id', 'N/A')}\nTweet: {tweet}\n---")

    return generated_content


if __name__ == "__main__":
    generate_content_from_config() 