from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ContentType(Enum):
    """Types of content that can be generated for a product."""
    REDDIT = "REDDIT"


class DistributionStatus(Enum):
    """Status of content distribution across channels."""
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


@dataclass
class DistributionMetadata:
    """Metadata for content distribution to a specific channel."""
    channel: str
    status: DistributionStatus
    published_at: Optional[datetime] = None
    channel_id: Optional[str] = None  # e.g., tweet ID
    channel_url: Optional[str] = None  # e.g., tweet URL
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        data = {
            'channel': self.channel,
            'status': self.status.value,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'channel_id': self.channel_id,
            'channel_url': self.channel_url,
            'error_message': self.error_message
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DistributionMetadata':
        """Create metadata from dictionary."""
        published_at = None
        if data.get('published_at'):
            try:
                published_at = datetime.fromisoformat(data['published_at'])
            except ValueError:
                pass

        return cls(
            channel=data['channel'],
            status=DistributionStatus(data['status']),
            published_at=published_at,
            channel_id=data.get('channel_id'),
            channel_url=data.get('channel_url'),
            error_message=data.get('error_message')
        )


@dataclass
class Product:
    """Product data model."""
    product_id: str
    name: str
    affiliate_link: Optional[str] = None
    content: Optional[str] = None  # Generic content field (was tweet_text)
    content_type: Optional[ContentType] = None  # Type of content (e.g. TWEET)
    identifier: Optional[str] = None
    screenshot_path: Optional[str] = None  # Path to the product screenshot
    distribution_metadata: List[DistributionMetadata] = None  # Track distribution status per channel

    def __post_init__(self):
        """Initialize default values after dataclass initialization."""
        if self.distribution_metadata is None:
            self.distribution_metadata = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary using dataclasses.asdict for simplicity."""
        data = asdict(self)
        # Convert ContentType enum to string for serialization
        if data.get('content_type'):
            data['content_type'] = data['content_type'].value
        # Convert distribution metadata to list of dicts
        data['distribution_metadata'] = [meta.to_dict() for meta in self.distribution_metadata]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        """Create product from dictionary."""
        if isinstance(data, Product):
            return data
        
        # Handle content_type conversion from string to enum
        content_type = data.get('content_type')
        if content_type:
            try:
                content_type = ContentType(content_type)
            except ValueError:
                content_type = None

        # Handle distribution metadata conversion
        distribution_metadata = []
        if data.get('distribution_metadata'):
            distribution_metadata = [
                DistributionMetadata.from_dict(meta) 
                for meta in data['distribution_metadata']
            ]
        
        return cls(
            product_id=data.get('product_id', ''),
            name=data.get('name', ''),
            affiliate_link=data.get('affiliate_link'),
            content=data.get('content'),
            content_type=content_type,
            identifier=data.get('identifier'),
            screenshot_path=data.get('screenshot_path'),
            distribution_metadata=distribution_metadata
        )

    @staticmethod
    def generate_identifier(product_id: str) -> str:
        return f"{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}" 