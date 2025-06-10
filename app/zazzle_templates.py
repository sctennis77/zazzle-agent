"""
Zazzle Templates module for managing product templates and configurations.

This module provides data structures and utilities for managing Zazzle product templates,
including customizable fields, template configurations, and template retrieval.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class CustomizableField:
    """
    Represents a customizable field in a Zazzle product template.
    
    Attributes:
        type: The type of field (e.g., 'image', 'text', 'color')
        description: A human-readable description of the field's purpose
        max_length: Optional maximum length for text fields
        formats: Optional list of supported file formats for media fields
        max_size_mb: Optional maximum file size in megabytes for media fields
        options: Optional list of valid options for selection fields
    """
    type: str
    description: str
    max_length: Optional[int] = None
    formats: Optional[List[str]] = None
    max_size_mb: Optional[int] = None
    options: Optional[List[str]] = None

@dataclass
class ZazzleTemplateConfig:
    """
    Configuration for a Zazzle product template.
    
    Attributes:
        product_type: The type of product (e.g., 'Sticker', 'T-Shirt')
        zazzle_template_id: The unique identifier for the Zazzle template
        original_url: The original Zazzle product URL
        zazzle_tracking_code: The tracking code for affiliate links
        customizable_fields: Dictionary mapping field names to their configurations
    """
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

# List of all available templates
ALL_TEMPLATES: List[ZazzleTemplateConfig] = [ZAZZLE_STICKER_TEMPLATE]

def get_product_template(product_type: str) -> Optional[ZazzleTemplateConfig]:
    """
    Retrieves a product template by type.
    
    Args:
        product_type: The type of product to find (case-insensitive)
        
    Returns:
        The matching ZazzleTemplateConfig if found, None otherwise
        
    Example:
        >>> template = get_product_template("sticker")
        >>> if template:
        ...     print(f"Found template: {template.product_type}")
    """
    for template in ALL_TEMPLATES:
        if template.product_type.lower() == product_type.lower():
            return template
    return None 