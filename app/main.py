import os
import logging
import json
import glob
import argparse
from typing import List, Dict, Optional, Any, Union
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
import csv
import asyncio
import sys

from app.affiliate_linker import ZazzleAffiliateLinker, ZazzleAffiliateLinkerError, InvalidProductDataError
from app.content_generator import ContentGenerator
from app.models import ProductInfo, PipelineConfig
from app.agents.reddit_agent import RedditAgent
from app.zazzle_templates import get_product_template, ZAZZLE_STICKER_TEMPLATE
from app.image_generator import ImageGenerator
from app.utils.logging_config import setup_logging
from app.zazzle_product_designer import ZazzleProductDesigner
from app.clients.imgur_client import ImgurClient
from app.pipeline import Pipeline
from app.db.database import init_db, SessionLocal
from app.db.models import PipelineRun, ErrorLog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Log the loaded API key (masked)
openai_api_key_loaded = os.getenv('OPENAI_API_KEY')
if openai_api_key_loaded:
    logger.info(f"OPENAI_API_KEY loaded: {openai_api_key_loaded[:5]}...{openai_api_key_loaded[-5:]}")
else:
    logger.warning("OPENAI_API_KEY not loaded.")

def ensure_output_dir(output_dir: str = 'outputs'):
    """Ensure the output directory exists."""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'screenshots'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'images'), exist_ok=True)
    logger.info("Ensured outputs directory exists")

def save_to_csv(products, output_file='processed_products.csv'):
    """Save product information to a CSV file."""
    if not isinstance(products, list):
        products = [products]

    # Convert products to dictionaries
    product_dicts = [product.to_dict() for product in products]
    
    # Determine output directory
    output_dir = os.getenv('OUTPUT_DIR', None)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, output_file)

    # Check if file exists to determine if we need to write headers
    file_exists = os.path.exists(output_file)
    
    mode = 'a' if file_exists else 'w'
    
    with open(output_file, mode, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=product_dicts[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(product_dicts)

def log_product_info(product_info: ProductInfo):
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

async def run_full_pipeline(config: PipelineConfig = None, model: str = "dall-e-3"):
    """Run the full pipeline: find post, generate image, create product."""
    session = SessionLocal()
    # Create a PipelineRun record at the start of the pipeline run
    pipeline_run = PipelineRun(status='started', start_time=datetime.utcnow())
    session.add(pipeline_run)
    session.commit()  # Commit to assign an ID to pipeline_run
    try:
        # Initialize configuration if not provided
        if config is None:
            config = PipelineConfig(
                model=model,
                zazzle_template_id=ZAZZLE_STICKER_TEMPLATE.zazzle_template_id,
                zazzle_tracking_code=ZAZZLE_STICKER_TEMPLATE.zazzle_tracking_code,
                prompt_version="1.0.0"
            )

        # Initialize all pipeline components (session and pipeline_run_id can be passed as needed)
        reddit_agent = RedditAgent(config_or_model=config.model)
        content_generator = ContentGenerator()
        image_generator = ImageGenerator(model=config.model)
        zazzle_designer = ZazzleProductDesigner()
        affiliate_linker = ZazzleAffiliateLinker()
        imgur_client = ImgurClient()

        # Create and run the pipeline (session and pipeline_run_id can be passed to components)
        pipeline = Pipeline(
            reddit_agent=reddit_agent,
            content_generator=content_generator,
            image_generator=image_generator,
            zazzle_designer=zazzle_designer,
            affiliate_linker=affiliate_linker,
            imgur_client=imgur_client,
            config=config
        )

        products = await pipeline.run_pipeline()
        
        if products:
            # Save products to CSV and log results
            save_to_csv(products)
            for product in products:
                product.log()
            # Mark pipeline run as successful
            pipeline_run.status = 'success'
        else:
            logger.warning("No products were generated")
            # Mark pipeline run as completed but with no products
            pipeline_run.status = 'no_products'
        # Set end time and commit status update
        pipeline_run.end_time = datetime.utcnow()
        session.commit()
        return products if products else []
        
    except Exception as e:
        logger.error(f"Error in full pipeline: {str(e)}")
        # Mark pipeline run as failed and log the error
        pipeline_run.status = 'error'
        pipeline_run.end_time = datetime.utcnow()
        session.add(ErrorLog(pipeline_run_id=pipeline_run.id, error_message=str(e)))
        session.commit()
        raise
    finally:
        # Always close the session to avoid connection leaks
        session.close()

async def run_generate_image_pipeline(image_prompt: str, model: str = "dall-e-2"):
    """Run the image generation pipeline with a given prompt."""
    image_generator = ImageGenerator(model=model)
    try:
        imgur_url, local_path = await image_generator.generate_image(image_prompt)
        logger.info(f"\nGenerated Image URL: {imgur_url}")
        logger.info(f"Generated Image Local Path: {local_path}")
    except Exception as e:
        logger.error(f"Error generating image: {e}")

async def main():
    """Main entry point for the application."""
    try:
        # Initialize the database
        init_db()
        
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Run the Zazzle Agent pipeline')
        parser.add_argument('--mode', type=str, default='full', choices=['full', 'image'],
                          help='Pipeline mode: full (complete pipeline) or image (image generation only)')
        parser.add_argument('--model', type=str, default='dall-e-3',
                          help='AI model to use (default: dall-e-3)')
        parser.add_argument('--prompt', type=str,
                          help='Image prompt (required for image mode)')
        args = parser.parse_args()

        # Validate arguments based on mode
        if args.mode == 'image':
            if not args.prompt:
                logger.error("--prompt is required for image mode")
                sys.exit(2)
            await run_generate_image_pipeline(args.prompt, args.model)
        else:  # full mode
            await run_full_pipeline(model=args.model)
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == '__main__':
    asyncio.run(main()) 