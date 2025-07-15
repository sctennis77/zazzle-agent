"""
Content generation module for the Zazzle Agent application.

This module provides functionality for generating content for Zazzle products using OpenAI's GPT models.
It supports both single and batch content generation, with error handling and logging.

The module handles:
- Single product content generation
- Batch processing of multiple products
- Configuration file processing
- OpenAI API integration
- Error handling and logging
"""

import json
import logging
import os
from typing import Dict, List, Optional, Union

import httpx
from dotenv import load_dotenv
from openai import OpenAI

from app.models import PipelineConfig, ProductIdea, ProductInfo, RedditContext
from app.utils.logging_config import get_logger
from app.utils.openai_usage_tracker import log_session_summary, track_openai_call

load_dotenv()

logger = get_logger(__name__)


class ContentGenerator:
    """
    Generates content for Zazzle products using OpenAI's GPT models.

    This class provides methods to generate content for individual products
    or batches of products, with support for error handling and logging.

    The class supports:
    - Single product content generation
    - Batch processing of multiple products
    - OpenAI API integration
    - Error handling and logging
    - Content validation
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the ContentGenerator with an OpenAI API key.

        Args:
            api_key (str, optional): OpenAI API key. If not provided, uses 'test_api_key'
                for testing purposes.
        """
        self.api_key = api_key or "test_api_key"
        self.client = OpenAI(api_key=self.api_key)
        logger.info("Initializing ContentGenerator")

    def _make_openai_call(self, prompt: str) -> str:
        """
        Make an OpenAI API call with tracking.

        Args:
            prompt: The prompt to send to OpenAI

        Returns:
            str: The response content
        """
        model = self._get_model()
        
        # Apply tracking with the actual model being used
        @track_openai_call(model=model, operation="chat")
        def _tracked_call():
            response = self.client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
            
        return _tracked_call()
    
    def _get_model(self) -> str:
        """
        Get the model to use for content generation.
        Uses the OPENAI_IDEA_MODEL environment variable, defaults to gpt-4o-mini.
        """
        return os.getenv("OPENAI_IDEA_MODEL", "gpt-4o-mini")

    def generate_content(
        self, product_name: str, force_new_content: bool = False
    ) -> str:
        """
        Generate content for a product using OpenAI's GPT model.

        Args:
            product_name (str): Name of the product to generate content for
            force_new_content (bool, optional): Whether to force generation of new content
                even if cached content exists. Defaults to False.

        Returns:
            str: Generated content in JSON format, or error message if generation fails

        Raises:
            Exception: If content generation fails
        """
        try:
            prompt = f"Create a content for the product: {product_name}"

            logger.info(f"Generating content for product: {product_name}")
            content = self._make_openai_call(prompt)

            try:
                # Validate that the content is valid JSON
                json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Generated content is not valid JSON for {product_name}")
                return "Error generating content"

            logger.info(f"Successfully generated content for {product_name}")
            return content

        except Exception as e:
            logger.error(f"Error generating content for {product_name}: {e}")
            return "Error generating content"

    def generate_content_batch(
        self, products: List[ProductInfo], force_new_content: bool = False
    ) -> List[ProductInfo]:
        """
        Generate content for a batch of products.

        Args:
            products (List[ProductInfo]): List of ProductInfo objects to process
            force_new_content (bool, optional): Whether to force generation of new content
                even if cached content exists. Defaults to False.

        Returns:
            List[ProductInfo]: List of processed ProductInfo objects with updated
                design instructions containing generated content
        """
        processed_products = []
        for product in products:
            try:
                content = self.generate_content(product.name, force_new_content)
                # Update the product's design instructions with the generated content
                product.design_instructions["content"] = content
                processed_products.append(product)
            except Exception as e:
                logger.error(f"Error processing product {product.product_id}: {e}")

        # Log session summary after batch processing
        log_session_summary()
        return processed_products


def generate_content_from_config(
    config_file: str = "app/products_config.json",
) -> Optional[Dict[str, str]]:
    """
    Generate content for products defined in a configuration file.

    Args:
        config_file (str): Path to the JSON configuration file containing product data.
            Defaults to 'app/products_config.json'.

    Returns:
        Optional[Dict[str, str]]: Dictionary mapping product IDs to generated content,
            or None if an error occurs

    Raises:
        FileNotFoundError: If the configuration file is not found
        json.JSONDecodeError: If the configuration file contains invalid JSON
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        return None

    generator = ContentGenerator(api_key=openai_api_key)

    try:
        with open(config_file, "r") as f:
            products_data = json.load(f)
        logger.info(f"Successfully loaded product data from {config_file}")

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from configuration file: {config_file}")
        return None
    except Exception as e:
        logger.error(f"Error reading configuration file: {e}")
        return None

    generated_content = {}
    for product in products_data:
        product_details = {
            "title": product.get(
                "name", f"Product ID: {product.get('product_id', 'N/A')}"
            ),
            "product_id": product.get("product_id", "N/A"),
        }
        content = generator.generate_content(product_details["title"])
        generated_content[product.get("product_id", "N/A")] = content
        logger.info(f"Generated content for product {product_details['product_id']}")

    # Log session summary after processing all products
    log_session_summary()
    return generated_content


if __name__ == "__main__":
    generate_content_from_config()
