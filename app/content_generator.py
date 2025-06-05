import os
import logging
from typing import Dict
import openai
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContentGenerator:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        
        openai.api_key = self.api_key

    def generate_tweet(self, product_data: Dict[str, str]) -> str:
        """
        Generate a tweet-sized description for a product using GPT-4.
        
        Args:
            product_data: Dictionary containing product information
                - title: Product title
                - product_id: Zazzle product ID
        
        Returns:
            str: Generated tweet text
        """
        try:
            prompt = f"""Create an engaging, tweet-sized description (max 280 characters) for this Zazzle product:
            Title: {product_data['title']}
            
            The description should:
            - Be engaging and persuasive
            - Include relevant hashtags
            - Be under 280 characters
            - Not include the word 'Zazzle'
            - Focus on the product's unique features or appeal
            """

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a creative marketing copywriter specializing in social media content."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )

            tweet_text = response.choices[0].message.content.strip()
            logger.info(f"Generated tweet for product: {product_data['title']}")
            return tweet_text

        except Exception as e:
            logger.error(f"Error generating tweet: {str(e)}")
            return ""

    def generate_tweets_batch(self, products: list) -> list:
        """
        Generate tweets for a batch of products.
        
        Args:
            products: List of product dictionaries
        
        Returns:
            list: List of dictionaries with tweets added
        """
        processed_products = []
        
        for product in products:
            tweet_text = self.generate_tweet(product)
            product['tweet_text'] = tweet_text
            processed_products.append(product)
            
        return processed_products 