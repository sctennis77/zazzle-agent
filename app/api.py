import logging
import os
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, get_db, init_db
from app.db.models import PipelineRun, ProductInfo, RedditPost, PipelineRunUsage
from app.models import GeneratedProductSchema, PipelineRunSchema, PipelineRunUsageSchema
from app.models import ProductInfo as ProductInfoDataClass
from app.models import ProductInfoSchema, RedditContext, RedditPostSchema
from app.pipeline_status import PipelineStatus
from app.utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
    ],  # Allow all common Vite dev ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize the database when the application starts."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully!")


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and Kubernetes."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


def model_to_dict(obj):
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def fetch_successful_pipeline_runs(db: Session) -> List[GeneratedProductSchema]:
    """
    Fetch all successful pipeline runs and their related data from the database.

    Returns:
        List[GeneratedProductSchema]: A list of Pydantic models containing product information,
        pipeline run details, and associated Reddit post data.
    """
    try:
        logger.info("Fetching successful pipeline runs...")
        pipeline_runs = (
            db.query(PipelineRun).filter_by(status=PipelineStatus.COMPLETED.value).all()
        )
        logger.info(f"Found {len(pipeline_runs)} completed pipeline runs.")
        products = []
        for run in pipeline_runs:
            try:
                logger.info(f"Processing pipeline run {run.id}")
                product_info = (
                    db.query(ProductInfo).filter_by(pipeline_run_id=run.id).first()
                )
                if not product_info:
                    logger.warning(f"No product info found for pipeline run {run.id}")
                    continue
                logger.info(f"Found product info: {product_info.id}")

                reddit_post = run.reddit_posts[0] if run.reddit_posts else None
                if not reddit_post:
                    logger.warning(f"No reddit post found for pipeline run {run.id}")
                    continue
                logger.info(f"Found reddit post: {reddit_post.post_id}")

                # Convert ORM models to in-memory models
                reddit_context = RedditContext(
                    post_id=reddit_post.post_id,
                    post_title=reddit_post.title,
                    post_url=reddit_post.url,
                    subreddit=reddit_post.subreddit,
                    post_content=reddit_post.content,
                    permalink=reddit_post.permalink,
                    comments=(
                        [{"text": reddit_post.comment_summary}]
                        if reddit_post.comment_summary
                        else [] or []
                    ),
                )

                product_info_data = ProductInfoDataClass(
                    product_id=str(product_info.id),
                    name=product_info.theme,
                    product_type=product_info.product_type,
                    image_url=product_info.image_url,
                    product_url=product_info.product_url,
                    zazzle_template_id=product_info.template_id,
                    zazzle_tracking_code="",  # This should come from config
                    theme=product_info.theme,
                    model=product_info.model,
                    prompt_version=product_info.prompt_version,
                    reddit_context=reddit_context,
                    design_instructions={
                        "description": product_info.design_description
                    },
                    affiliate_link=product_info.affiliate_link,
                )

                # Convert to Pydantic schemas using model_validate
                try:
                    product_schema = ProductInfoSchema.model_validate(product_info)
                    pipeline_schema = PipelineRunSchema.model_validate(run)
                    reddit_schema = RedditPostSchema.model_validate(reddit_post)
                    
                    # Fetch usage data
                    usage_data = db.query(PipelineRunUsage).filter_by(pipeline_run_id=run.id).first()
                    usage_schema = PipelineRunUsageSchema.model_validate(usage_data) if usage_data else None

                    products.append(
                        GeneratedProductSchema(
                            product_info=product_schema,
                            pipeline_run=pipeline_schema,
                            reddit_post=reddit_schema,
                            usage=usage_schema,
                        )
                    )
                    logger.info(
                        f"Successfully converted pipeline run {run.id} to schema with usage data"
                    )
                except Exception as e:
                    logger.error(
                        f"Error converting pipeline run {run.id} to schema: {str(e)}"
                    )
                    logger.error(traceback.format_exc())
                    continue
            except Exception as e:
                logger.error(f"Error processing pipeline run {run.id}: {str(e)}")
                logger.error(traceback.format_exc())
                continue
        logger.info(f"Returning {len(products)} products.")
        return products
    except Exception as e:
        logger.error(f"Error in fetch_successful_pipeline_runs: {str(e)}")
        logger.error(traceback.format_exc())
        raise


@app.get("/api/generated_products", response_model=List[GeneratedProductSchema])
async def get_generated_products():
    """
    API endpoint to retrieve all successful pipeline runs and their related data.

    Returns:
        List[GeneratedProductSchema]: A list of Pydantic models containing product information,
        pipeline run details, and associated Reddit post data.

    Raises:
        HTTPException: If there is an error fetching the data from the database or
            converting the data to Pydantic models.
    """
    db = SessionLocal()
    try:
        logger.info("Starting get_generated_products request")
        products = fetch_successful_pipeline_runs(db)
        try:
            # Convert ORM models to Pydantic schemas
            result = [
                GeneratedProductSchema.model_validate(product) for product in products
            ]
            logger.info(
                f"Successfully converted {len(result)} products to response format"
            )
            return result
        except Exception as e:
            logger.error(f"Error converting models to Pydantic schemas: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Error converting data to response format: {str(e)}",
            )
    except Exception as e:
        logger.error(f"Error in get_generated_products: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting API server...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
