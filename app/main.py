import argparse
import asyncio
import csv
import glob
import json
import logging
import os
import sys
import random
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv

from app.affiliate_linker import (
    InvalidProductDataError,
    ZazzleAffiliateLinker,
    ZazzleAffiliateLinkerError,
)
from app.agents.reddit_agent import AVAILABLE_SUBREDDITS, RedditAgent, pick_subreddit
from app.clients.imgur_client import ImgurClient
from app.content_generator import ContentGenerator
from app.db.database import SessionLocal, init_db
from app.db.models import ErrorLog, PipelineRun
from app.image_generator import ImageGenerator
from app.models import PipelineConfig, ProductInfo
from app.pipeline import Pipeline
from app.pipeline_status import PipelineStatus
from app.utils.logging_config import setup_logging
from app.utils.openai_usage_tracker import log_session_summary
from app.zazzle_product_designer import ZazzleProductDesigner
from app.zazzle_templates import ZAZZLE_PRINT_TEMPLATE, get_product_template

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Log the loaded API key (masked)
openai_api_key_loaded = os.getenv("OPENAI_API_KEY")
if openai_api_key_loaded:
    logger.info(
        f"OPENAI_API_KEY loaded: {openai_api_key_loaded[:5]}...{openai_api_key_loaded[-5:]}"
    )
else:
    logger.warning("OPENAI_API_KEY not loaded.")


def ensure_output_dir(output_dir: str = "outputs") -> None:
    """Ensure the output directory exists."""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "screenshots"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
    logger.info("Ensured outputs directory exists")


def save_to_csv(products: List[ProductInfo], output_file: str = "processed_products.csv") -> None:
    """Save product information to a CSV file."""
    if not isinstance(products, list):
        products = [products]

    # Convert products to dictionaries
    product_dicts = [product.to_dict() for product in products]

    # Determine output directory
    output_dir = os.getenv("OUTPUT_DIR", None)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, output_file)

    # Check if file exists to determine if we need to write headers
    file_exists = os.path.exists(output_file)

    mode = "a" if file_exists else "w"

    with open(output_file, mode, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=product_dicts[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(product_dicts)


def log_product_info(product_info: ProductInfo) -> None:
    """Log product information in a readable format."""
    logger.info("\nGenerated Product Info:")
    logger.info(f"Theme: {product_info.theme}")
    logger.info(f"Model: {product_info.model}")
    logger.info(f"Prompt Version: {product_info.prompt_version}")

    logger.info("\nReddit Context:")
    logger.info(f"Post Title: {product_info.reddit_context.post_title}")
    logger.info(f"Post URL: {product_info.reddit_context.post_url}")

    logger.info("\nProduct URL:")
    logger.info("To view and customize the product, open this URL in your browser:")
    logger.info(f"{product_info.product_url}")

    logger.info("\nGenerated Image URL:")
    logger.info(f"{product_info.image_url}")


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def run_full_pipeline(
    config: Optional[PipelineConfig] = None, 
    subreddit_name: Optional[str] = None,
    max_subreddit_attempts: int = 5
) -> List[ProductInfo]:
    """
    Run the complete product generation pipeline with subreddit cycling.

    Args:
        config (PipelineConfig): The pipeline configuration object. Defaults to a config with model 'dall-e-3'.
        subreddit_name (Optional[str]): The subreddit to use. If None, random subreddits will be selected.
        max_subreddit_attempts (int): Maximum number of subreddits to try before giving up.

    Returns:
        List[ProductInfo]: List of generated product information.
    """
    if config is None:
        config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id=ZAZZLE_PRINT_TEMPLATE.zazzle_template_id,
            zazzle_tracking_code=ZAZZLE_PRINT_TEMPLATE.zazzle_tracking_code,
            prompt_version="1.0.0",
        )

    # Track attempted subreddits to avoid duplicates
    attempted_subreddits = set()
    
    # If a specific subreddit is provided, validate it and use it first
    if subreddit_name:
        validate_subreddit(subreddit_name)
        attempted_subreddits.add(subreddit_name)
        logger.info(f"Using specified subreddit: {subreddit_name}")
    else:
        subreddit_name = pick_subreddit()
        attempted_subreddits.add(subreddit_name)
        logger.info(f"Selected subreddit: {subreddit_name}")

    for attempt in range(max_subreddit_attempts):
        try:
            logger.info(f"Attempting subreddit {attempt + 1}/{max_subreddit_attempts}: {subreddit_name}")
            
            with session_scope() as session:
                # Create pipeline run
                pipeline_run = PipelineRun(
                    status=PipelineStatus.STARTED.value, start_time=datetime.utcnow()
                )
                session.add(pipeline_run)
                session.commit()

                # Initialize components
                reddit_agent = RedditAgent(
                    config,
                    pipeline_run_id=pipeline_run.id,
                    session=session,
                    subreddit_name=subreddit_name,
                )
                content_generator = ContentGenerator()
                image_generator = ImageGenerator(model=config.model)
                zazzle_designer = ZazzleProductDesigner()
                affiliate_linker = ZazzleAffiliateLinker(
                    zazzle_affiliate_id=os.getenv("ZAZZLE_AFFILIATE_ID", ""),
                    zazzle_tracking_code=os.getenv("ZAZZLE_TRACKING_CODE", ""),
                )
                imgur_client = ImgurClient()

                # Create and run pipeline
                pipeline = Pipeline(
                    reddit_agent=reddit_agent,
                    content_generator=content_generator,
                    image_generator=image_generator,
                    zazzle_designer=zazzle_designer,
                    affiliate_linker=affiliate_linker,
                    imgur_client=imgur_client,
                    config=config,
                    pipeline_run_id=pipeline_run.id,
                    session=session,
                )

                # Run pipeline and get results
                results = await pipeline.run_pipeline()
                logger.info(f"Pipeline results: {results}")

                # If we got results, we're done!
                if results:
                    # Save results to CSV if any products were generated
                    output_dir = os.getenv("OUTPUT_DIR", "outputs")
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, "processed_products.csv")
                    save_to_csv(results, output_file)

                    # Update pipeline run status and end time
                    pipeline_run.status = PipelineStatus.COMPLETED.value
                    pipeline_run.end_time = datetime.utcnow()
                    session.add(pipeline_run)
                    session.commit()

                    # Log OpenAI API usage summary
                    log_session_summary()

                    logger.info(f"Successfully generated products from subreddit: {subreddit_name}")
                    return results
                else:
                    logger.warning(f"No products generated from subreddit: {subreddit_name}")
                    
        except Exception as e:
            logger.warning(f"Failed to generate products from subreddit {subreddit_name}: {str(e)}")
            
        # If we get here, this subreddit failed. Try the next one
        if attempt < max_subreddit_attempts - 1:
            # Pick a new subreddit that we haven't tried yet
            available_subreddits = [s for s in AVAILABLE_SUBREDDITS if s not in attempted_subreddits]
            if not available_subreddits:
                logger.error("No more subreddits available to try")
                break
                
            subreddit_name = random.choice(available_subreddits)
            attempted_subreddits.add(subreddit_name)
            logger.info(f"Moving to next subreddit: {subreddit_name}")
        else:
            logger.error(f"Failed to generate products after trying {max_subreddit_attempts} subreddits")
            break

    # If we get here, all attempts failed
    error_msg = f"Failed to generate products after trying {len(attempted_subreddits)} subreddits: {list(attempted_subreddits)}"
    logger.error(error_msg)
    # Log OpenAI API usage summary even on failure
    log_session_summary()
    raise Exception(error_msg)


async def run_generate_image_pipeline(image_prompt: str, model: str = "dall-e-2") -> None:
    """Run the image generation pipeline with a given prompt."""
    image_generator = ImageGenerator(model=model)
    try:
        imgur_url, local_path = await image_generator.generate_image(image_prompt)
        logger.info(f"\nGenerated Image URL: {imgur_url}")
        logger.info(f"Generated Image Local Path: {local_path}")
    except Exception as e:
        logger.error(f"Error generating image: {e}")


def validate_subreddit(subreddit_name: str) -> None:
    """
    Validate that the given subreddit name is in the available subreddits list.

    Args:
        subreddit_name: The subreddit name to validate

    Raises:
        ValueError: If the subreddit is not in the available list
    """
    if subreddit_name not in AVAILABLE_SUBREDDITS:
        raise ValueError(
            f"Subreddit '{subreddit_name}' is not available. "
            f"Available subreddits: {AVAILABLE_SUBREDDITS}"
        )


async def main() -> None:
    """Main entry point for the application."""
    try:
        # Initialize the database
        init_db()

        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Run the Zazzle Agent pipeline")
        parser.add_argument(
            "--mode",
            type=str,
            default="full",
            choices=["full", "image"],
            help="Pipeline mode: full (complete pipeline) or image (image generation only)",
        )
        parser.add_argument(
            "--model",
            type=str,
            default="dall-e-3",
            help="AI model to use (default: dall-e-3)",
        )
        parser.add_argument(
            "--prompt", type=str, help="Image prompt (required for image mode)"
        )
        parser.add_argument(
            "--subreddit",
            type=str,
            help="Subreddit to use (optional, will pick randomly if not specified)",
        )
        args = parser.parse_args()

        # Validate arguments based on mode
        if args.mode == "image":
            if not args.prompt:
                logger.error("--prompt is required for image mode")
                sys.exit(2)
            await run_generate_image_pipeline(args.prompt, args.model)
        else:  # full mode
            await run_full_pipeline(subreddit_name=args.subreddit)
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
