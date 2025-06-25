from datetime import datetime

from app.db.database import SessionLocal
from app.db.models import PipelineRun, ProductInfo, RedditPost


def check_pipeline_db():
    session = SessionLocal()
    try:
        # Get the most recent pipeline run
        pipeline_run = (
            session.query(PipelineRun).order_by(PipelineRun.start_time.desc()).first()
        )
        print("\n=== Most Recent Pipeline Run ===")
        print(f"ID: {pipeline_run.id}")
        print(f"Status: {pipeline_run.status}")
        print(f"Start Time: {pipeline_run.start_time}")
        print(f"End Time: {pipeline_run.end_time}")
        print(f"Config: {pipeline_run.config}")

        # Get associated RedditPost
        reddit_post = session.query(RedditPost).first()
        print("\n=== Reddit Post ===")
        print(f"ID: {reddit_post.id}")
        print(f"Post ID: {reddit_post.post_id}")
        print(f"Title: {reddit_post.title}")
        print(f"Subreddit: {reddit_post.subreddit}")
        print(f"Content: {reddit_post.content}")
        print(f"URL: {reddit_post.url}")

        # Get associated ProductInfo
        product_info = session.query(ProductInfo).first()
        print("\n=== Product Info ===")
        print(f"ID: {product_info.id}")
        print(f"Product ID: {product_info.product_id}")
        print(f"Name: {product_info.name}")
        print(f"Product Type: {product_info.product_type}")
        print(f"Image URL: {product_info.image_url}")
        print(f"Product URL: {product_info.product_url}")
        print(f"Theme: {product_info.theme}")
        print(f"Model: {product_info.model}")
        print(f"Prompt Version: {product_info.prompt_version}")

    finally:
        session.close()


if __name__ == "__main__":
    check_pipeline_db()
