from abc import ABC, abstractmethod
from typing import Optional
from app.models import Product, DistributionMetadata, DistributionStatus


class DistributionError(Exception):
    """Base exception for distribution-related errors."""
    pass


class DistributionChannel(ABC):
    """Abstract base class for distribution channels."""

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Return the name of the distribution channel."""
        pass

    @abstractmethod
    def publish(self, product: Product) -> DistributionMetadata:
        """Publish content to the distribution channel.
        
        Args:
            product: The product to publish content for.
            
        Returns:
            DistributionMetadata: Metadata about the publication status.
        """
        pass

    @abstractmethod
    def get_publication_url(self, channel_id: str) -> Optional[str]:
        """Get the URL for a published piece of content.
        
        Args:
            channel_id: The channel-specific ID of the published content.
            
        Returns:
            Optional[str]: The URL of the published content, or None if not found.
        """
        return None

    def _create_metadata(self, status: DistributionStatus, channel_id: Optional[str] = None,
                        channel_url: Optional[str] = None, error_message: Optional[str] = None) -> DistributionMetadata:
        """Create distribution metadata for this channel.
        
        Args:
            status: The distribution status.
            channel_id: Optional channel-specific ID for the published content.
            channel_url: Optional URL for the published content.
            error_message: Optional error message if publication failed.
            
        Returns:
            DistributionMetadata: The created metadata.
        """
        return DistributionMetadata(
            channel=self.channel_name,
            status=status,
            channel_id=channel_id,
            channel_url=channel_url,
            error_message=error_message
        ) 