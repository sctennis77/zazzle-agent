"""
Subreddit Publisher for posting commissioned products to Reddit.

This module provides functionality to publish generated products as image posts
to specific subreddits, with a focus on the /clouvel subreddit for commissioned content.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.clients.reddit_client import RedditClient
from app.db.database import SessionLocal
from app.db.models import (
    PipelineRun,
    PipelineRunUsage,
    ProductInfo,
    ProductSubredditPost,
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


class SubredditPublisher:
    """
    Publisher for posting generated products to Reddit subreddits.

    This class handles fetching products from the database, preparing them
    for posting, and submitting them as image posts to specified subreddits.

    Supports context manager pattern for automatic session cleanup:

        with SubredditPublisher(dry_run=True) as publisher:
            result = publisher.publish_product('1')
    """

    def __init__(self, dry_run: bool = True, session: Optional[Session] = None):
        """
        Initialize the SubredditPublisher.

        Args:
            dry_run: Whether to run in dry run mode (default: True)
            session: Optional SQLAlchemy session for database operations
        """
        self.dry_run = dry_run
        self.subreddit = "clouvel"  # Hardcoded to clouvel subreddit
        self.session = session or SessionLocal()

        # Initialize Reddit client with dry run mode
        os.environ["REDDIT_MODE"] = "dryrun" if dry_run else "live"
        self.reddit_client = RedditClient()

        logger.info(
            f"Initialized SubredditPublisher for r/{self.subreddit} (dry_run: {dry_run})"
        )

    def publish_product(self, product_id: str) -> Dict[str, Any]:
        """
        Publish a product to the configured subreddit.

        Args:
            product_id: The ID of the product to publish

        Returns:
            Dict containing the result of the publishing operation

        Example:
            # Recommended: Use context manager for automatic cleanup
            with SubredditPublisher(dry_run=True) as publisher:
                result = publisher.publish_product('1')

            # Alternative: Manual cleanup (remember to call .close())
            publisher = SubredditPublisher(dry_run=True)
            result = publisher.publish_product('1')
            publisher.close()
        """
        try:
            logger.info(f"Starting product publication for product_id: {product_id}")

            # Fetch and validate product
            generated_product = self.get_product_from_db(product_id)
            if not generated_product:
                raise ValueError(f"Product with ID {product_id} not found in database")

            # Check if already posted
            if self._is_product_already_posted(product_id):
                raise ValueError(f"Product {product_id} has already been posted")

            # Submit the image post directly
            submitted_post = self.submit_image_post(generated_product)

            # Save the submitted post to database
            saved_post = self.save_submitted_post_to_db(product_id, submitted_post)

            logger.info(
                f"Successfully published product {product_id} to r/{self.subreddit}"
            )

            return {
                "success": True,
                "product_id": product_id,
                "subreddit": self.subreddit,
                "submitted_post": submitted_post,
                "saved_post": saved_post,
                "dry_run": self.dry_run,
            }

        except Exception as e:
            logger.error(f"Failed to publish product {product_id}: {e}")
            return {
                "success": False,
                "product_id": product_id,
                "subreddit": self.subreddit,
                "error": str(e),
                "dry_run": self.dry_run,
            }

    def get_product_from_db(self, product_id: str) -> Optional[GeneratedProductSchema]:
        """
        Fetch a product from the database by product_id.

        Args:
            product_id: The ID of the product to fetch

        Returns:
            GeneratedProductSchema if found, None otherwise
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
                return None

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
            return generated_product

        except Exception as e:
            logger.error(f"Error fetching product {product_id} from database: {e}")
            raise

    def _is_product_already_posted(self, product_id: str) -> bool:
        """
        Check if a product has already been posted to any subreddit.

        Args:
            product_id: The ID of the product to check

        Returns:
            True if the product has already been posted, False otherwise
        """
        existing_post = (
            self.session.query(ProductSubredditPost)
            .filter(ProductSubredditPost.product_info_id == product_id)
            .first()
        )
        return existing_post is not None

    def submit_image_post(
        self, generated_product: GeneratedProductSchema
    ) -> Dict[str, Any]:
        """
        Submit an image post to Reddit for a generated product.

        Args:
            generated_product: The generated product to post

        Returns:
            Dict containing the submission result
        """
        try:
            product = generated_product.product_info
            reddit_post = generated_product.reddit_post

            # Use the generated image title instead of theme, fallback to theme if no image_title
            post_title = product.image_title or product.theme

            # Create title for the image post
            title = f"🎨 {post_title} - commissioned by u/{reddit_post.author or 'Anonymous'}"

            # Create content for the image post
            content = f"""
**Commissioned Artwork: {product.theme}**

This piece was commissioned by u/{reddit_post.author or 'Anonymous'} from r/{reddit_post.subreddit} and brought to life by Clouvel, the mythic golden retriever who illustrates Reddit stories! 🐕✨

**Original Post:** [{reddit_post.title}]({reddit_post.url})

Clouvel's summary of the comments:

> {reddit_post.comment_summary}


*Commissioned content - supporting the Reddit community through art! 🎨*


[View in Clouvel Gallery](https://clouvel.com/gallery?product={product.id}) | [Commission a Post](https://clouvel.com)

---
*Posted by Clouvel 🐕❤️*
            """.strip()

            # Submit the image post using the Reddit client
            result = self.reddit_client.submit_image_post(
                subreddit_name=self.subreddit,
                title=title,
                content=content,
                image_url=product.image_url,
            )

            logger.info(
                f"Submitted image post for product {product.id} to r/{self.subreddit}"
            )
            return result

        except Exception as e:
            logger.error(f"Error submitting image post: {e}")
            raise

    def save_submitted_post_to_db(
        self, product_id: str, submitted_post: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save the submitted post information to the database.
        Args:
            product_id: The ID of the original product
            submitted_post: The result from the Reddit submission
        Returns:
            Dict containing the saved post information
        """
        try:
            # Create new record (validation should have already checked for duplicates)
            post_record = ProductSubredditPost(product_info_id=product_id)

            post_record.subreddit_name = submitted_post.get("subreddit", self.subreddit)
            post_record.reddit_post_id = submitted_post.get("post_id")
            post_record.reddit_post_url = submitted_post.get("post_url")
            post_record.reddit_post_title = submitted_post.get("title")
            post_record.submitted_at = submitted_post.get(
                "submitted_at", datetime.now(timezone.utc)
            )
            post_record.dry_run = self.dry_run
            post_record.status = submitted_post.get("status", "published")
            post_record.error_message = submitted_post.get("error_message")
            post_record.engagement_data = submitted_post.get("engagement_data")

            self.session.add(post_record)
            self.session.commit()
            logger.info(
                f"Saved ProductSubredditPost for product {product_id} (dry_run: {self.dry_run})"
            )
            return {
                "product_id": product_id,
                "subreddit": post_record.subreddit_name,
                "reddit_post_id": post_record.reddit_post_id,
                "reddit_post_url": post_record.reddit_post_url,
                "submitted_at": post_record.submitted_at,
                "dry_run": post_record.dry_run,
                "status": post_record.status,
                "error_message": post_record.error_message,
                "engagement_data": post_record.engagement_data,
            }
        except Exception as e:
            logger.error(f"Error saving submitted post: {e}")
            raise

    def clear_productsubredditpost_from_db(self, product_id: str) -> Dict[str, Any]:
        """
        Clear a ProductSubredditPost record from the database.

        Args:
            product_id: The ID of the product whose post record to clear

        Returns:
            Dict containing the result of the clearing operation

        Example:
            # Recommended: Use context manager for automatic cleanup
            with SubredditPublisher(dry_run=True) as publisher:
                result = publisher.clear_productsubredditpost_from_db('1')

            # Alternative: Manual cleanup (remember to call .close())
            publisher = SubredditPublisher(dry_run=True)
            result = publisher.clear_productsubredditpost_from_db('1')
            publisher.close()
        """
        try:
            logger.info(f"Clearing ProductSubredditPost for product_id: {product_id}")

            # Find and delete the existing post record
            existing_post = (
                self.session.query(ProductSubredditPost)
                .filter(ProductSubredditPost.product_info_id == product_id)
                .first()
            )

            if not existing_post:
                logger.warning(
                    f"No existing ProductSubredditPost found for product {product_id}"
                )
                return {
                    "success": False,
                    "product_id": product_id,
                    "error": f"No existing ProductSubredditPost found for product {product_id}",
                }

            # Store info before deletion
            post_info = {
                "product_id": product_id,
                "subreddit": existing_post.subreddit_name,
                "reddit_post_id": existing_post.reddit_post_id,
                "reddit_post_url": existing_post.reddit_post_url,
                "submitted_at": existing_post.submitted_at,
                "dry_run": existing_post.dry_run,
                "status": existing_post.status,
            }

            # Delete the post record
            self.session.delete(existing_post)
            self.session.commit()

            logger.info(
                f"Successfully cleared ProductSubredditPost for product {product_id}"
            )

            return {
                "success": True,
                "product_id": product_id,
                "cleared_post": post_info,
                "message": f"ProductSubredditPost for product {product_id} has been cleared from database",
            }

        except Exception as e:
            logger.error(
                f"Failed to clear ProductSubredditPost for product {product_id}: {e}"
            )
            return {"success": False, "product_id": product_id, "error": str(e)}
        finally:
            # Note: We don't close the session here because it might be shared
            # The caller should manage the session lifecycle
            pass

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
