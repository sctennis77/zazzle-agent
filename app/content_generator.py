import os
import json
import logging
from typing import List, Dict
import httpx
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentGenerator:
    def __init__(self, api_key: str):
        logger.info("Initializing ContentGenerator")
        http_client = httpx.Client(proxies=None)
        self.client = OpenAI(api_key=api_key, http_client=http_client)

    def generate_tweet_content(self, product_details: Dict[str, str]) -> str:
        """
        Generates tweet-sized content for a given product.
        
        Args:
            product_details: Dictionary containing product information (e.g., 'title', 'product_id').
        
        Returns:
            Generated tweet content.
        """
        logger.info(f"Generating tweet content for product: {product_details.get('title', 'N/A')}")
        title = product_details.get('title', 'Zazzle Product')
        product_id = product_details.get('product_id', 'N/A')

        prompt = f"Create a concise and engaging tweet (under 280 characters) for the following Zazzle product:\nTitle: {title}\n\nFocus on highlighting its appeal to potential buyers. Include relevant emojis and hashtags. Do not include any links or affiliate information, just the tweet text."

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a marketing assistant generating tweet content."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=60, # Keep response short for tweets
                temperature=0.7
            )
            tweet_text = response.choices[0].message.content.strip()
            logger.info(f"Successfully generated tweet for {title}")
            return tweet_text

        except Exception as e:
            logger.error(f"Error generating tweet content for {title}: {e}")
            return "Error generating tweet content."

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
        tweet = generator.generate_tweet_content(product_details)
        generated_content[product.get('product_id', 'N/A')] = tweet
        print(f"Product ID: {product.get('product_id', 'N/A')}\nTweet: {tweet}\n---")

    return generated_content


if __name__ == "__main__":
    generate_content_from_config() 