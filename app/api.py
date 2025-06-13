from fastapi import FastAPI, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from app.db.database import get_db

# Assuming these are the data models
from app.db.models import PipelineRun, ProductInfo, RedditPost

app = FastAPI()

def fetch_successful_pipeline_runs(db: Session) -> List[dict]:
    """
    Fetch all successful pipeline runs and their related data from the database.

    Args:
        db (Session): The database session used to query the database.

    Returns:
        List[dict]: A list of dictionaries containing product information, pipeline run details, and associated Reddit post data.
    """
    pipeline_runs = db.query(PipelineRun).filter_by(status='success').all()
    products = []
    for run in pipeline_runs:
        product_info = db.query(ProductInfo).filter_by(pipeline_run_id=run.id).first()
        reddit_post = db.query(RedditPost).filter_by(id=run.reddit_post_id).first()
        products.append({
            "product_info": product_info,
            "pipeline_run": run,
            "reddit_post": reddit_post
        })
    return products

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
        raise HTTPException(status_code=500, detail="Internal Server Error")