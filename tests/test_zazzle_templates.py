import pytest
from app.zazzle_templates import (
    CustomizableField,
    ZazzleTemplateConfig,
    ZAZZLE_STICKER_TEMPLATE,
    get_product_template,
    ALL_TEMPLATES
)

def test_customizable_field():
    """Test CustomizableField creation and properties."""
    field = CustomizableField(
        type="image",
        description="A test image field",
        max_length=100,
        formats=["png", "jpg"],
        max_size_mb=5,
        options=["option1", "option2"]
    )
    assert field.type == "image"
    assert field.description == "A test image field"
    assert field.max_length == 100
    assert field.formats == ["png", "jpg"]
    assert field.max_size_mb == 5
    assert field.options == ["option1", "option2"]

def test_zazzle_template_config():
    """Test ZazzleTemplateConfig creation and properties."""
    fields = {
        "image": CustomizableField(
            type="image",
            description="Test image field",
            formats=["png"],
            max_size_mb=5
        )
    }
    config = ZazzleTemplateConfig(
        product_type="Test Product",
        zazzle_template_id="123",
        original_url="https://example.com",
        zazzle_tracking_code="TEST",
        customizable_fields=fields
    )
    assert config.product_type == "Test Product"
    assert config.zazzle_template_id == "123"
    assert config.original_url == "https://example.com"
    assert config.zazzle_tracking_code == "TEST"
    assert "image" in config.customizable_fields
    assert config.customizable_fields["image"].type == "image"

def test_zazzle_sticker_template():
    """Test the predefined ZAZZLE_STICKER_TEMPLATE."""
    assert ZAZZLE_STICKER_TEMPLATE.product_type == "Sticker"
    assert ZAZZLE_STICKER_TEMPLATE.zazzle_template_id == "256689990112831136"
    assert "image" in ZAZZLE_STICKER_TEMPLATE.customizable_fields
    assert ZAZZLE_STICKER_TEMPLATE.customizable_fields["image"].type == "image"

def test_get_product_template():
    """Test get_product_template returns the correct template or None."""
    template = get_product_template("Sticker")
    assert template == ZAZZLE_STICKER_TEMPLATE
    template = get_product_template("STICKER")
    assert template == ZAZZLE_STICKER_TEMPLATE
    template = get_product_template("nonexistent")
    assert template is None

def test_all_templates():
    """Test ALL_TEMPLATES contains the sticker template and is a list."""
    assert isinstance(ALL_TEMPLATES, list)
    assert ZAZZLE_STICKER_TEMPLATE in ALL_TEMPLATES
    for template in ALL_TEMPLATES:
        assert isinstance(template, ZazzleTemplateConfig)
        assert hasattr(template, "product_type")
        assert hasattr(template, "zazzle_template_id")
        assert hasattr(template, "original_url")
        assert hasattr(template, "zazzle_tracking_code")
        assert hasattr(template, "customizable_fields")
        assert isinstance(template.customizable_fields, dict) 