#!/usr/bin/env python3

from app.db.database import SessionLocal
from app.db.models import PipelineRun, RedditPost, ProductInfo, ErrorLog
from datetime import datetime

def check_db():
    session = SessionLocal()
    try:
        # Get all pipeline runs
        pipeline_runs = session.query(PipelineRun).all()
        print("\n=== Pipeline Runs ===")
        for run in pipeline_runs:
            print(f"\nPipeline Run ID: {run.id}")
            print(f"Status: {run.status}")
            print(f"Start Time: {run.start_time}")
            print(f"End Time: {run.end_time}")
            print(f"Duration: {run.duration}")
            print(f"Last Error: {run.last_error}")
            
            # Get associated Reddit posts
            reddit_posts = session.query(RedditPost).filter_by(pipeline_run_id=run.id).all()
            print(f"\nReddit Posts ({len(reddit_posts)}):")
            for post in reddit_posts:
                print(f"\n  Post ID: {post.post_id}")
                print(f"  Title: {post.title}")
                print(f"  Subreddit: {post.subreddit}")
                print(f"  URL: {post.url}")
                
                # Get associated products
                products = session.query(ProductInfo).filter_by(reddit_post_id=post.id).all()
                print(f"\n  Products ({len(products)}):")
                for product in products:
                    print(f"\n    Theme: {product.theme}")
                    print(f"    Image URL: {product.image_url}")
                    print(f"    Product URL: {product.product_url}")
                    print(f"    Affiliate Link: {product.affiliate_link}")
                    print(f"    Template ID: {product.template_id}")
                    print(f"    Model: {product.model}")
                    print(f"    Product Type: {product.product_type}")
            
            # Get error logs
            error_logs = session.query(ErrorLog).filter_by(pipeline_run_id=run.id).all()
            print(f"\nError Logs ({len(error_logs)}):")
            for error in error_logs:
                print(f"\n  Error Type: {error.error_type}")
                print(f"  Component: {error.component}")
                print(f"  Message: {error.error_message}")
                print(f"  Timestamp: {error.timestamp}")
                
    finally:
        session.close()

if __name__ == "__main__":
    check_db() 