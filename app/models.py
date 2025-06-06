from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ContentType(Enum):
    """Types of content that can be generated for a product."""
    TWEET = "TWEET"


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary using dataclasses.asdict for simplicity."""
        data = asdict(self)
        # Convert ContentType enum to string for serialization
        if data.get('content_type'):
            data['content_type'] = data['content_type'].value
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
        
        return cls(
            product_id=data.get('product_id', ''),
            name=data.get('name', ''),
            affiliate_link=data.get('affiliate_link'),
            content=data.get('content'),  # Map old tweet_text to content
            content_type=content_type,
            identifier=data.get('identifier'),
            screenshot_path=data.get('screenshot_path')
        )

    @staticmethod
    def generate_identifier(product_id: str) -> str:
        return f"{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}" 