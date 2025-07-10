import logging
import os
import random
from contextlib import contextmanager
from datetime import datetime
from typing import List, Optional

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

# Expose FastAPI app for Uvicorn
from app.api import app
