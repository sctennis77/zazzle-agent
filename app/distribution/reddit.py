import logging
import os
from typing import Optional

from app.distribution.base import DistributionChannel, DistributionError
from app.models import DistributionMetadata, DistributionStatus, ProductInfo

logger = logging.getLogger(__name__)


class RedditDistributionError(DistributionError):
    """Reddit-specific distribution errors."""

    pass


class RedditDistributionChannel(DistributionChannel):
    """Reddit distribution channel implementation."""

    def __init__(self):
        """Initialize Reddit distribution channel."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # Check for required credentials
        required_vars = [
            "REDDIT_CLIENT_ID",
            "REDDIT_CLIENT_SECRET",
            "REDDIT_USERNAME",
            "REDDIT_PASSWORD",
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            self.logger.warning(
                "⚠️ Reddit API credentials are missing. Required variables: "
                + ", ".join(missing_vars)
            )
        else:
            self.logger.info("Reddit API credentials found. Channel is ready to use.")

    @property
    def channel_name(self) -> str:
        """Return the name of the distribution channel."""
        return "reddit"

    def publish(self, product_info: ProductInfo) -> DistributionMetadata:
        """Publish content to Reddit."""
        try:
            # TODO: Implement actual Reddit API call
            # For now, we'll mock the response
            return DistributionMetadata(
                channel="reddit",
                status=DistributionStatus.PUBLISHED,
                published_at=None,  # Would be set in real implementation
                channel_id="mock_post_id",
                channel_url="https://reddit.com/r/mock_subreddit/comments/mock_post_id",
            )
        except Exception as e:
            raise RedditDistributionError(f"Failed to publish to Reddit: {str(e)}")

    def get_publication_url(self, channel_id: str) -> Optional[str]:
        """Get the URL for a published post."""
        # For now, we'll just construct the URL
        return f"https://reddit.com/r/mock_subreddit/comments/{channel_id}"

    def _create_metadata(
        self, status: DistributionStatus, error_message: Optional[str] = None
    ) -> DistributionMetadata:
        """Create distribution metadata."""
        return DistributionMetadata(
            channel="reddit", status=status, error_message=error_message
        )
