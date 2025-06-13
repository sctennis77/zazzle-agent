from fastapi import FastAPI, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.pipeline_status import PipelineStatus
import logging
import os
import uvicorn
import traceback

# Assuming these are the data models
from app.db.models import PipelineRun, ProductInfo, RedditPost

app = FastAPI()

def model_to_dict(obj):
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

def fetch_successful_pipeline_runs(db: Session) -> List[dict]:
    """
    Fetch all successful pipeline runs and their related data from the database.

    Args:
        db (Session): The database session used to query the database.

    Returns:
        List[dict]: A list of dictionaries containing product information, pipeline run details, and associated Reddit post data.
    """
    try:
        logging.info(f"Database URL: {os.getenv('DATABASE_URL', 'sqlite:///zazzle_pipeline.db')}")
        logging.info("Fetching successful pipeline runs...")
        pipeline_runs = db.query(PipelineRun).filter_by(status=PipelineStatus.COMPLETED.value).all()
        logging.info(f"Found {len(pipeline_runs)} completed pipeline runs.")
        products = []
        for run in pipeline_runs:
            try:
                logging.info(f"Processing pipeline run {run.id}")
                product_info = db.query(ProductInfo).filter_by(pipeline_run_id=run.id).first()
                logging.info(f"Found product info: {product_info}")
                reddit_post = run.reddit_posts[0] if run.reddit_posts else None
                logging.info(f"Found reddit post: {reddit_post}")
                products.append({
                    "product_info": model_to_dict(product_info),
                    "pipeline_run": model_to_dict(run),
                    "reddit_post": model_to_dict(reddit_post)
                })
            except Exception as e:
                logging.error(f"Error processing pipeline run {run.id}: {str(e)}")
                logging.error(traceback.format_exc())
                raise
        logging.info(f"Returning {len(products)} products.")
        return products
    except Exception as e:
        logging.error(f"Error in fetch_successful_pipeline_runs: {str(e)}")
        logging.error(traceback.format_exc())
        raise

@app.get("/api/generated_products")
async def get_generated_products(db: Session = Depends(get_db)) -> List[dict]:
    """
    API endpoint to retrieve all successful pipeline runs and their related data.

    This endpoint fetches data from the database and returns a list of products,
    each containing product information, pipeline run details, and associated Reddit post data.

    Args:
        db (Session): The database session used to query the database.

    Returns:
        List[dict]: A list of dictionaries containing product information, pipeline run details, and associated Reddit post data.
    """
    try:
        return fetch_successful_pipeline_runs(db)
    except Exception as e:
        logging.error(f"Exception in get_generated_products: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)