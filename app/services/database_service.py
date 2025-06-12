from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.db.models import (
    PipelineRun, RedditPost, ProductInfo, ErrorLog, CommentSummary,
    Base
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

class DatabaseService:
    def __init__(self, session: Session):
        self.session = session

    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(self.session.get_bind())
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise

    def create_pipeline_run(self, config: Optional[Dict[str, Any]] = None) -> PipelineRun:
        """Create a new pipeline run."""
        try:
            pipeline_run = PipelineRun(
                status='pending',
                config=config
            )
            self.session.add(pipeline_run)
            self.session.commit()
            logger.info(f"Created pipeline run: {pipeline_run.id}")
            return pipeline_run
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error creating pipeline run: {str(e)}")
            raise

    def get_pipeline_run(self, run_id: int) -> Optional[PipelineRun]:
        """Get a pipeline run by ID."""
        try:
            return self.session.query(PipelineRun).filter_by(id=run_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting pipeline run {run_id}: {str(e)}")
            raise

    def update_pipeline_run_status(self, run_id: int, status: str, summary: Optional[str] = None) -> Optional[PipelineRun]:
        """Update the status of a pipeline run."""
        try:
            run = self.get_pipeline_run(run_id)
            if run:
                run.status = status
                if summary:
                    run.summary = summary
                self.session.commit()
                logger.info(f"Updated pipeline run {run_id} status to {status}")
            return run
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error updating pipeline run {run_id} status: {str(e)}")
            raise

    def add_reddit_post(self, pipeline_run_id: int, post_data: Dict[str, Any]) -> RedditPost:
        """Add a new Reddit post to the database."""
        try:
            post = RedditPost(
                pipeline_run_id=pipeline_run_id,
                post_id=post_data['id'],
                title=post_data['title'],
                content=post_data.get('content'),
                subreddit=post_data['subreddit'],
                url=post_data['url'],
                permalink=post_data.get('permalink')
            )
            self.session.add(post)
            self.session.commit()
            logger.info(f"Added Reddit post: {post.post_id}")
            return post
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error adding Reddit post: {str(e)}")
            raise

    def add_comment_summary(self, reddit_post_id: int, summary: str) -> CommentSummary:
        """Add a new comment summary to the database."""
        try:
            comment = CommentSummary(
                reddit_post_id=reddit_post_id,
                summary=summary
            )
            self.session.add(comment)
            self.session.commit()
            logger.info(f"Added comment summary for post {reddit_post_id}")
            return comment
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error adding comment summary: {str(e)}")
            raise

    def add_product_info(self, pipeline_run_id: int, reddit_post_id: int, product_data: Dict[str, Any]) -> ProductInfo:
        """Add a new product info to the database."""
        try:
            product = ProductInfo(
                pipeline_run_id=pipeline_run_id,
                reddit_post_id=reddit_post_id,
                theme=product_data['theme'],
                image_url=product_data['image_url'],
                product_url=product_data['product_url'],
                affiliate_link=product_data.get('affiliate_link'),
                template_id=product_data['template_id'],
                model=product_data['model'],
                prompt_version=product_data['prompt_version'],
                product_type=product_data['product_type'],
                design_description=product_data.get('design_description')
            )
            self.session.add(product)
            self.session.commit()
            logger.info(f"Added product info: {product.id}")
            return product
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error adding product info: {str(e)}")
            raise

    def log_error(self, pipeline_run_id: int, error_data: Dict[str, Any]) -> ErrorLog:
        """Log an error for a pipeline run."""
        try:
            error = ErrorLog(
                pipeline_run_id=pipeline_run_id,
                error_message=error_data['error_message'],
                error_type=error_data.get('error_type', 'SYSTEM_ERROR'),
                component=error_data.get('component', 'PIPELINE'),
                stack_trace=error_data.get('stack_trace'),
                context_data=error_data.get('context_data'),
                severity=error_data.get('severity', 'ERROR')
            )
            self.session.add(error)
            self.session.commit()
            logger.info(f"Logged error for pipeline run {pipeline_run_id}")
            return error
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Error logging error: {str(e)}")
            raise

    def get_pipeline_runs(self, status: Optional[str] = None) -> List[PipelineRun]:
        """Get all pipeline runs, optionally filtered by status."""
        try:
            query = self.session.query(PipelineRun)
            if status:
                query = query.filter_by(status=status)
            return query.order_by(PipelineRun.start_time.desc()).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting pipeline runs: {str(e)}")
            raise

    def get_reddit_posts(self, pipeline_run_id: int) -> List[RedditPost]:
        """Get all Reddit posts for a pipeline run."""
        try:
            return self.session.query(RedditPost).filter_by(pipeline_run_id=pipeline_run_id).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting Reddit posts: {str(e)}")
            raise

    def get_product_infos(self, pipeline_run_id: int) -> List[ProductInfo]:
        """Get all product infos for a pipeline run."""
        try:
            return self.session.query(ProductInfo).filter_by(pipeline_run_id=pipeline_run_id).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting product infos: {str(e)}")
            raise

    def get_error_logs(self, pipeline_run_id: int) -> List[ErrorLog]:
        """Get all error logs for a pipeline run."""
        try:
            return self.session.query(ErrorLog).filter_by(pipeline_run_id=pipeline_run_id).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting error logs: {str(e)}")
            raise 