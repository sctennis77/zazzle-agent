# Orchestrates the full product generation workflow

import csv
import json
import logging
import os
from datetime import datetime
from typing import Dict, List

from dotenv import load_dotenv

from app.design_generator import create_design_generator
from app.metadata_generator import MetadataGenerator
from app.publish_to_zazzle import publish_to_zazzle
from app.zazzle_url_generator import ZazzleUrlGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ZazzleAgent:
    def __init__(self):
        """Initialize the Zazzle agent with all required components."""
        load_dotenv()

        # Initialize components
        self.design_generator = create_design_generator()
        self.metadata_generator = MetadataGenerator()
        self.zazzle_url_generator = ZazzleUrlGenerator()

        # Load configuration
        self.products_per_batch = int(os.getenv("PRODUCTS_PER_BATCH", "5"))
        self.design_style = os.getenv("DESIGN_STYLE", "modern")
        self.target_niche = os.getenv("TARGET_NICHE", "home decor")
        self.output_dir = os.getenv("OUTPUT_DIR", "outputs")
        self.csv_filename = os.getenv("CSV_FILENAME", "products.csv")

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_product(self, prompt: str) -> Dict:
        """
        Generate a single product with design, metadata, and Zazzle URL.

        Args:
            prompt: The design prompt for the product

        Returns:
            Dict containing all product data
        """
        try:
            # Generate design
            logger.info(f"Generating design for prompt: {prompt}")
            try:
                design_data = self.design_generator.generate_design(
                    prompt=prompt, style=self.design_style
                )
                logger.info(
                    f"Successfully generated design: {design_data['imgur_url']}"
                )
            except Exception as e:
                logger.error(f"Design generation failed: {str(e)}")
                if hasattr(e, "response"):
                    logger.error(
                        f"API Response: {e.response.text if hasattr(e.response, 'text') else e.response}"
                    )
                raise

            # Generate metadata
            logger.info("Generating product metadata")
            metadata = self.metadata_generator.generate_metadata(
                design_prompt=prompt, niche=self.target_niche, style=self.design_style
            )

            # Generate Zazzle URL
            logger.info("Generating Zazzle product URL")
            product_url = self.zazzle_url_generator.generate_product_url(
                image_url=design_data["imgur_url"],
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata["tags"],
            )

            # Publish to Zazzle
            logger.info("Publishing product to Zazzle...")
            cap_url = product_url  # Assuming product_url is the CAP link
            zazzle_email = os.getenv("ZAZZLE_EMAIL")
            zazzle_password = os.getenv("ZAZZLE_PASSWORD")

            if not all([cap_url, zazzle_email, zazzle_password]):
                logger.error(
                    "Missing required environment variables for publishing. Please set ZAZZLE_EMAIL and ZAZZLE_PASSWORD."
                )
            else:
                publish_to_zazzle(cap_url, zazzle_email, zazzle_password)

            # Combine all data
            return {
                "prompt": prompt,
                "design_url": design_data["imgur_url"],
                "title": metadata["title"],
                "description": metadata["description"],
                "tags": metadata["tags"],
                "product_url": product_url,
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to generate product: {str(e)}")
            raise

    def export_to_csv(self, products: List[Dict]):
        """
        Export generated products to a CSV file.

        Args:
            products: List of product data dictionaries
        """
        try:
            csv_path = os.path.join(self.output_dir, self.csv_filename)

            # Define CSV headers
            headers = [
                "prompt",
                "design_url",
                "title",
                "description",
                "tags",
                "product_url",
                "generated_at",
            ]

            # Write to CSV
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(products)

            logger.info(f"Exported {len(products)} products to {csv_path}")

        except Exception as e:
            logger.error(f"Failed to export products to CSV: {str(e)}")
            raise

    def run(self, prompts: List[str] = None):
        """
        Run the Zazzle agent to generate products.

        Args:
            prompts: Optional list of design prompts. If not provided,
                    will generate random prompts based on the target niche.
        """
        try:
            if not prompts:
                # Start with a single, simple test prompt
                prompts = ["A simple geometric pattern in blue and white"]

            products = []
            for prompt in prompts:
                try:
                    product = self.generate_product(prompt)
                    products.append(product)
                    logger.info(f"Successfully generated product: {product['title']}")
                except Exception as e:
                    logger.error(
                        f"Failed to generate product for prompt '{prompt}': {str(e)}"
                    )
                    continue

            # Export results
            if products:
                self.export_to_csv(products)
                logger.info(f"Successfully generated {len(products)} products")
            else:
                logger.warning("No products were generated successfully")

        except Exception as e:
            logger.error(f"Agent execution failed: {str(e)}")
            raise


def main():
    # Load environment variables
    load_dotenv()

    # Initialize components
    design_generator = create_design_generator()
    metadata_generator = MetadataGenerator()
    zazzle_url_generator = ZazzleUrlGenerator()

    # Example prompt
    prompt = "A simple geometric pattern in blue and white"

    # Generate design
    logger.info(f"Generating design for prompt: {prompt}")
    design_result = design_generator.generate_design(prompt)
    logger.info(f"Successfully generated design: {design_result['image_url']}")

    # Generate metadata
    logger.info("Generating product metadata")
    metadata = metadata_generator.generate_metadata(prompt)

    # Generate Zazzle product URL
    logger.info("Generating Zazzle product URL")
    product_url = zazzle_url_generator.generate_product_url(
        image_url=design_result["image_url"],
        title=metadata["title"],
        description=metadata["description"],
        tags=metadata["tags"],
    )
    logger.info(f"Successfully generated product URL: {product_url}")

    # Export to CSV (optional)
    # ... existing CSV export code ...


if __name__ == "__main__":
    main()
