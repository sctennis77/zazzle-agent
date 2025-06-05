from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


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
        """Convert product to dictionary."""
        return {
            'product_id': self.product_id,
            'name': self.name,
            'affiliate_link': self.affiliate_link,
            'tweet_text': self.tweet_text,
            'identifier': self.identifier,
            'screenshot_path': self.screenshot_path
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        """Create product from dictionary."""
        if isinstance(data, Product):
            return data
        return cls(
            product_id=data['product_id'],
            name=data['name'],
            affiliate_link=data.get('affiliate_link'),
            tweet_text=data.get('tweet_text'),
            identifier=data.get('identifier'),
            screenshot_path=data.get('screenshot_path')
        ) 