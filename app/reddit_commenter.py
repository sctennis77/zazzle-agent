"""
Reddit Commenter for posting commissioned products as comments on original posts.

This module provides functionality to comment on the original Reddit posts that inspired
commissioned products, creating direct engagement with the source community.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.clients.reddit_client import RedditClient
from app.db.database import SessionLocal
from app.db.models import (
    Donation,
    PipelineRun,
    PipelineRunUsage,
    PipelineTask,
    ProductInfo,
    ProductRedditComment,
    RedditPost,
)
from app.models import (
    GeneratedProductSchema,
    PipelineRunSchema,
    PipelineRunUsageSchema,
    ProductInfoSchema,
    RedditPostSchema,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class RedditCommenter:
    """
    Commenter for posting generated products as comments on original Reddit posts.

    This class handles fetching products from the database, preparing them
    for commenting, and submitting them as image comments to the original posts
    that inspired the commissioned artwork.

    Supports context manager pattern for automatic session cleanup:

        with RedditCommenter(dry_run=True) as commenter:
            result = commenter.comment_on_original_post('1')
    """

    def __init__(self, dry_run: bool = True, session: Optional[Session] = None):
        """
        Initialize the RedditCommenter.

        Args:
            dry_run: Whether to run in dry run mode (default: True)
            session: Optional SQLAlchemy session for database operations
        """
        self.dry_run = dry_run
        self.session = session or SessionLocal()

        # Initialize Reddit client with dry run mode
        os.environ["REDDIT_MODE"] = "dryrun" if dry_run else "live"
        self.reddit_client = RedditClient()

        logger.info(f"Initialized RedditCommenter (dry_run: {dry_run})")

    def comment_on_original_post(self, product_id: str) -> Dict[str, Any]:
        """
        Comment on the original post with the commissioned artwork.

        Args:
            product_id: The ID of the product to comment with

        Returns:
            Dict containing the result of the commenting operation

        Example:
            # Recommended: Use context manager for automatic cleanup
            with RedditCommenter(dry_run=True) as commenter:
                result = commenter.comment_on_original_post('1')

            # Alternative: Manual cleanup (remember to call .close())
            commenter = RedditCommenter(dry_run=True)
            result = commenter.comment_on_original_post('1')
            commenter.close()
        """
        try:
            logger.info(
                f"Starting comment on original post for product_id: {product_id}"
            )

            # Fetch and validate product
            generated_product, donation = self.get_product_from_db(product_id)
            if not generated_product:
                raise ValueError(f"Product with ID {product_id} not found in database")

            # Check if already commented
            if self._is_product_already_commented(product_id):
                raise ValueError(f"Product {product_id} has already been commented")

            # Submit the comment with image
            submitted_comment = self.submit_image_comment(generated_product, donation)

            # Save the submitted comment to database
            saved_comment = self.save_submitted_comment_to_db(
                product_id, submitted_comment
            )

            logger.info(
                f"Successfully commented on original post for product {product_id}"
            )

            return {
                "success": True,
                "product_id": product_id,
                "original_post_id": generated_product.reddit_post.post_id,
                "submitted_comment": submitted_comment,
                "saved_comment": saved_comment,
                "dry_run": self.dry_run,
            }

        except Exception as e:
            logger.error(
                f"Failed to comment on original post for product {product_id}: {e}"
            )
            return {
                "success": False,
                "product_id": product_id,
                "error": str(e),
                "dry_run": self.dry_run,
            }

    def get_product_from_db(
        self, product_id: str
    ) -> tuple[Optional[GeneratedProductSchema], Optional[object]]:
        """
        Fetch a product from the database by product_id.

        Args:
            product_id: The ID of the product to fetch

        Returns:
            Tuple of (GeneratedProductSchema, Donation) if found, (None, None) otherwise
        """
        try:
            # Query the database for the product
            product_info = (
                self.session.query(ProductInfo)
                .filter(ProductInfo.id == product_id)
                .first()
            )

            if not product_info:
                logger.warning(f"Product with ID {product_id} not found in database")
                return None, None

            # Get related data
            reddit_post = (
                self.session.query(RedditPost)
                .filter(RedditPost.id == product_info.reddit_post_id)
                .first()
            )

            pipeline_run = (
                self.session.query(PipelineRun)
                .filter(PipelineRun.id == product_info.pipeline_run_id)
                .first()
            )

            usage = (
                self.session.query(PipelineRunUsage)
                .filter(PipelineRunUsage.pipeline_run_id == pipeline_run.id)
                .first()
            )

            # Get commission data to access the correct reddit_username
            pipeline_task = None
            donation = None
            if pipeline_run:
                pipeline_task = (
                    self.session.query(PipelineTask)
                    .filter(PipelineTask.pipeline_run_id == pipeline_run.id)
                    .first()
                )
                if pipeline_task and pipeline_task.donation_id:
                    donation = (
                        self.session.query(Donation)
                        .filter(Donation.id == pipeline_task.donation_id)
                        .first()
                    )

            # Convert to schemas
            product_schema = ProductInfoSchema.from_orm(product_info)
            reddit_post_schema = (
                RedditPostSchema.from_orm(reddit_post) if reddit_post else None
            )
            pipeline_run_schema = (
                PipelineRunSchema.from_orm(pipeline_run) if pipeline_run else None
            )
            usage_schema = PipelineRunUsageSchema.from_orm(usage) if usage else None

            # Create GeneratedProductSchema
            generated_product = GeneratedProductSchema(
                product_info=product_schema,
                pipeline_run=pipeline_run_schema,
                reddit_post=reddit_post_schema,
                usage=usage_schema,
            )

            logger.info(f"Successfully fetched product {product_id} from database")
            return generated_product, donation

        except Exception as e:
            logger.error(f"Error fetching product {product_id} from database: {e}")
            raise

    def _get_commission_username(
        self, generated_product: GeneratedProductSchema, donation=None
    ) -> str:
        """
        Get the correct username to use for commission attribution.

        Args:
            generated_product: The generated product containing commission data
            donation: The donation object if available

        Returns:
            The username to use for commission attribution
        """
        # Check if we have commission data
        if donation:
            # Check if donation is anonymous
            if donation.is_anonymous:
                return "Anonymous"
            # Return the commission username
            return donation.reddit_username or "Anonymous"

        # Fallback to original post author if no commission data
        return generated_product.reddit_post.author or "Anonymous"

    def _is_product_already_commented(self, product_id: str) -> bool:
        """
        Check if a product has already been commented on any post.

        Args:
            product_id: The ID of the product to check

        Returns:
            True if the product has already been commented, False otherwise
        """
        existing_comment = (
            self.session.query(ProductRedditComment)
            .filter(ProductRedditComment.product_info_id == product_id)
            .first()
        )

        if existing_comment:
            return True

        return False

    def submit_image_comment(
        self, generated_product: GeneratedProductSchema, donation=None
    ) -> Dict[str, Any]:
        """
        Submit an image comment to Reddit for a generated product.

        Args:
            generated_product: The generated product to comment with
            donation: Optional donation associated with the product

        Returns:
            Dict containing the submission result
        """
        try:
            product = generated_product.product_info
            reddit_post = generated_product.reddit_post

            # Determine the commission username to use
            commission_username = self._get_commission_username(
                generated_product, donation
            )

            # Create content for the image comment
            comment_content = f"""Love this story! Created some art inspired by your post 🎨

{{image1}}

Commissioned by u/{commission_username} • Made with [Clouvel](https://clouvel.ai/?product={reddit_post.post_id})"""

            # Submit the image comment using the Reddit client
            result = self.reddit_client.comment_with_image(
                post_id=reddit_post.post_id,
                comment_text=comment_content,
                image_url=product.image_url,
            )

            logger.info(
                f"Submitted image comment for product {product.id} on post {reddit_post.post_id}"
            )
            return result

        except Exception as e:
            logger.error(f"Error submitting image comment: {e}")
            raise

    def save_submitted_comment_to_db(
        self, product_id: str, submitted_comment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save the submitted comment information to the database.

        Args:
            product_id: The ID of the original product
            submitted_comment: The result from the Reddit comment submission

        Returns:
            Dict containing the saved comment information
        """
        try:
            # Create new record for comment interaction
            comment_record = ProductRedditComment(product_info_id=product_id)

            comment_record.original_post_id = submitted_comment.get("post_id")
            comment_record.comment_id = submitted_comment.get("comment_id")
            comment_record.comment_url = submitted_comment.get("comment_url")
            comment_record.subreddit_name = submitted_comment.get("subreddit")
            comment_record.comment_content = submitted_comment.get("comment_text")
            comment_record.commented_at = submitted_comment.get(
                "submitted_at", datetime.now(timezone.utc)
            )
            comment_record.dry_run = self.dry_run
            comment_record.status = submitted_comment.get("status", "commented")
            comment_record.error_message = submitted_comment.get("error_message")
            comment_record.engagement_data = submitted_comment.get("engagement_data")

            self.session.add(comment_record)
            self.session.commit()
            logger.info(
                f"Saved ProductRedditComment record for product {product_id} (dry_run: {self.dry_run})"
            )
            return {
                "product_id": product_id,
                "original_post_id": comment_record.original_post_id,
                "comment_id": comment_record.comment_id,
                "comment_url": comment_record.comment_url,
                "subreddit": comment_record.subreddit_name,
                "commented_at": comment_record.commented_at,
                "dry_run": comment_record.dry_run,
                "status": comment_record.status,
                "error_message": comment_record.error_message,
                "engagement_data": comment_record.engagement_data,
            }
        except Exception as e:
            logger.error(f"Error saving submitted comment: {e}")
            raise

    def close(self):
        """Close the database session."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures session is closed."""
        self.close()
