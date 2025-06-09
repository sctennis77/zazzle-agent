from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class CustomizableField:
    type: str
    description: str
    max_length: Optional[int] = None
    formats: Optional[List[str]] = None
    max_size_mb: Optional[int] = None
    options: Optional[List[str]] = None

@dataclass
class ZazzleTemplateConfig:
    product_type: str
    zazzle_template_id: str
    original_url: str
    zazzle_tracking_code: str
    customizable_fields: Dict[str, CustomizableField]

# Define the Zazzle Sticker Template
ZAZZLE_STICKER_TEMPLATE = ZazzleTemplateConfig(
    product_type="Sticker",
    zazzle_template_id="256689990112831136",
    original_url="https://www.zazzle.com/beautiful_stickers_for_beautiful_moments-256689990112831136",
    zazzle_tracking_code="RedditStickerz_0",
    customizable_fields={
        "image": CustomizableField(
            type="image",
            description="Custom image to be displayed on the sticker",
            formats=["png", "jpg", "jpeg"],
            max_size_mb=5
        ),
  
    }
)

ALL_TEMPLATES: List[ZazzleTemplateConfig] = [ZAZZLE_STICKER_TEMPLATE]

def get_product_template(product_type: str) -> Optional[ZazzleTemplateConfig]:
    """Retrieves a product template by type."""
    for template in ALL_TEMPLATES:
        if template.product_type.lower() == product_type.lower():
            return template
    return None 