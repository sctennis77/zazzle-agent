"""
Zazzle Templates module for managing product templates and configurations.

This module provides data structures and utilities for managing Zazzle product templates,
including customizable fields, template configurations, and template retrieval.

The module provides:
- Data structures for template configurations and customizable fields
- Pre-defined templates for different product types
- Template retrieval and validation utilities
- Support for various field types (image, text, color, etc.)
- Configuration for file formats and size limits
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union

@dataclass
class CustomizableField:
    """
    Represents a customizable field in a Zazzle product template.
    
    This class defines the properties and constraints of a field that can be
    customized in a Zazzle product template, such as images, text, or colors.
    
    Attributes:
        type (str): The type of field (e.g., 'image', 'text', 'color')
        description (str): A human-readable description of the field's purpose
        max_length (Optional[int]): Optional maximum length for text fields
        formats (Optional[List[str]]): Optional list of supported file formats for media fields
        max_size_mb (Optional[int]): Optional maximum file size in megabytes for media fields
        options (Optional[List[str]]): Optional list of valid options for selection fields
    """
    type: str
    description: str
    max_length: Optional[int] = None
    formats: Optional[List[str]] = None
    max_size_mb: Optional[int] = None
    options: Optional[List[str]] = None

    def validate_value(self, value: Any) -> bool:
        """
        Validate a value against the field's constraints.
        
        Args:
            value (Any): The value to validate
            
        Returns:
            bool: True if the value is valid, False otherwise
            
        Note:
            Validation rules:
            - For text fields: checks length against max_length
            - For image fields: checks format and size
            - For selection fields: checks if value is in options
        """
        if self.type == 'text' and self.max_length:
            return len(str(value)) <= self.max_length
        elif self.type == 'image':
            if not isinstance(value, str):
                return False
            # Add image validation logic here
            return True
        elif self.type == 'selection' and self.options:
            return value in self.options
        return True

@dataclass
class ZazzleTemplateConfig:
    """
    Configuration for a Zazzle product template.
    
    This class defines the complete configuration for a Zazzle product template,
    including its type, identifiers, and customizable fields.
    
    Attributes:
        product_type (str): The type of product (e.g., 'Sticker', 'T-Shirt')
        zazzle_template_id (str): The unique identifier for the Zazzle template
        original_url (str): The original Zazzle product URL
        zazzle_tracking_code (str): The tracking code for affiliate links
        customizable_fields (Dict[str, CustomizableField]): Dictionary mapping field names to their configurations
    """
    product_type: str
    zazzle_template_id: str
    original_url: str
    zazzle_tracking_code: str
    customizable_fields: Dict[str, CustomizableField]

    def validate_fields(self, field_values: Dict[str, Any]) -> bool:
        """
        Validate all field values against their configurations.
        
        Args:
            field_values (Dict[str, Any]): Dictionary of field names and their values
            
        Returns:
            bool: True if all values are valid, False otherwise
            
        Note:
            Checks each field value against its corresponding CustomizableField
            configuration using the validate_value method.
        """
        for field_name, value in field_values.items():
            if field_name not in self.customizable_fields:
                return False
            if not self.customizable_fields[field_name].validate_value(value):
                return False
        return True

# TODO improve logic for multiple templates
# Define the Zazzle Sticker Template
ZAZZLE_STICKER_TEMPLATE = ZazzleTemplateConfig(
    product_type="Sticker",
    zazzle_template_id="256577895504131235",
    original_url="https://www.zazzle.com/beautiful_stickers_for_beautiful_moments-256689990112831136",
    zazzle_tracking_code="Clouvel-0",
    customizable_fields={
        "image": CustomizableField(
            type="image",
            description="Custom image to be displayed on the sticker",
            formats=["png", "jpg", "jpeg"],
            max_size_mb=5
        ),
    }
)

ZAZZLE_PRINT_TEMPLATE = ZazzleTemplateConfig(
    product_type="Print",
    zazzle_template_id="256344169523425346",
    original_url="https://www.zazzle.com/stories_from_reddit_inspired_masterpieces_faux_canvas_print-256344169523425346",
    zazzle_tracking_code="Clouvel-0",
    customizable_fields={
        "image": CustomizableField(
            type="image",
            description="Custom image to be displayed on the print",
            formats=["png", "jpg", "jpeg"],
            max_size_mb=5
        ),
    }
)


# List of all available templates
ALL_TEMPLATES: List[ZazzleTemplateConfig] = [ZAZZLE_PRINT_TEMPLATE]

def get_product_template(product_type: str) -> Optional[ZazzleTemplateConfig]:
    """
    Retrieves a product template by type.
    
    Args:
        product_type (str): The type of product to find (case-insensitive)
        
    Returns:
        Optional[ZazzleTemplateConfig]: The matching template configuration if found,
            None otherwise
        
    Example:
        >>> template = get_product_template("sticker")
        >>> if template:
        ...     print(f"Found template: {template.product_type}")
    """
    for template in ALL_TEMPLATES:
        if template.product_type.lower() == product_type.lower():
            return template
    return None 