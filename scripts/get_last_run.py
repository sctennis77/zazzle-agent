from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.database_service import DatabaseService
from app.db.models import Base, CommentSummary
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

def main():
    # Create database connection
    engine = create_engine('sqlite:///zazzle_pipeline.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Initialize database service
    db_service = DatabaseService(session)
    
    try:
        # Get the most recent pipeline run
        pipeline_runs = db_service.get_pipeline_runs()
        if not pipeline_runs:
            print("No pipeline runs found in the database.")
            return
            
        latest_run = pipeline_runs[0]
        print(f"\n=== Latest Pipeline Run (ID: {latest_run.id}) ===")
        print(f"Status: {latest_run.status}")
        print(f"Start Time: {latest_run.start_time}")
        print(f"End Time: {latest_run.end_time}")
        print(f"Summary: {latest_run.summary}")
        
        # Get Reddit posts for this run
        reddit_posts = db_service.get_reddit_posts(latest_run.id)
        if reddit_posts:
            print("\n=== Reddit Posts ===")
            for post in reddit_posts:
                print(f"\nPost ID: {post.post_id}")
                print(f"Title: {post.title}")
                print(f"Subreddit: {post.subreddit}")
                print(f"URL: {post.url}")
                
                # Get comment summary
                comment_summary = session.query(CommentSummary).filter_by(reddit_post_id=post.id).first()
                if comment_summary:
                    print(f"Comment Summary: {comment_summary.summary}")
        
        # Get product information
        products = db_service.get_product_infos(latest_run.id)
        if products:
            print("\n=== Generated Products ===")
            for product in products:
                print(f"\nTheme: {product.theme}")
                print(f"Product Type: {product.product_type}")
                print(f"Image URL: {product.image_url}")
                print(f"Product URL: {product.product_url}")
                print(f"Affiliate Link: {product.affiliate_link}")
                print(f"Model Used: {product.model}")
                print(f"Prompt Version: {product.prompt_version}")
                if product.design_description:
                    print(f"Design Description: {product.design_description}")
        
        # Get any error logs
        errors = db_service.get_error_logs(latest_run.id)
        if errors:
            print("\n=== Error Logs ===")
            for error in errors:
                print(f"\nError Type: {error.error_type}")
                print(f"Component: {error.component}")
                print(f"Message: {error.error_message}")
                print(f"Severity: {error.severity}")
                if error.stack_trace:
                    print(f"Stack Trace: {error.stack_trace}")
    
    except Exception as e:
        logger.error(f"Error fetching pipeline run data: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main() 