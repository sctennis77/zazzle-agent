from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class CustomizableField:
    type: str
    description: str
    max_length: Optional[int] = None
    formats: Optional[List[str]] = None
    max_size_mb: Optional[int] = None

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
    zazzle_template_id="256026928356227568",
    original_url="https://www.zazzle.com/fire_away_vintage_cannon_golf_ball_sticker-256026928356227568?t_text1_txt=Osprey%20Valley%20Golf%20Mecca&color=Blue&quantity=6&t_image1_iid=4b2bbb87-ee28-47a3-9de9-5ddb045ec8bc&ed=True&r=4834233&dz=ad291f5e-9048-4ab9-9ca9-10757e8f7555",
    zazzle_tracking_code="stickerattempt1",
    customizable_fields={
        "text": CustomizableField(
            type="text",
            description="Custom text to be displayed on the sticker",
            max_length=100
        ),
        "image": CustomizableField(
            type="image",
            description="Custom image to be displayed on the sticker",
            formats=["png", "jpg", "jpeg"],
            max_size_mb=5
        )
    }
)

ALL_TEMPLATES: List[ZazzleTemplateConfig] = [ZAZZLE_STICKER_TEMPLATE]

def get_product_template(product_type: str) -> Optional[ZazzleTemplateConfig]:
    """Retrieves a product template by type."""
    for template in ALL_TEMPLATES:
        if template.product_type.lower() == product_type.lower():
            return template
    return None 