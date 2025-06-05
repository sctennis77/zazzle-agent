from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Product:
    """Product data model."""
    product_id: str
    name: str
    affiliate_link: Optional[str] = None
    tweet_text: Optional[str] = None
    identifier: Optional[str] = None
    screenshot_path: Optional[str] = None  # Path to the product screenshot

    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary using dataclasses.asdict for simplicity."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        """Create product from dictionary."""
        if isinstance(data, Product):
            return data
        return cls(
            product_id=data.get('product_id', ''),
            name=data.get('name', ''),
            affiliate_link=data.get('affiliate_link'),
            tweet_text=data.get('tweet_text'),
            identifier=data.get('identifier'),
            screenshot_path=data.get('screenshot_path')
        )

    @staticmethod
    def generate_identifier(product_id: str) -> str:
        return f"{product_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}" 