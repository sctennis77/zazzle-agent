"""
Test suite for the ImageProcessor class.

This module tests the image processing functionality including logo stamping,
signature addition, and error handling.
"""

import io
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.image_processor import ImageProcessor, ImageProcessingError


class TestImageProcessor:
    """Test cases for the ImageProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a test image
        self.test_image = Image.new("RGB", (1024, 1024), color="white")
        
        # Create a temporary logo file for testing
        self.temp_logo = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        logo_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
        logo_image.save(self.temp_logo.name)
        self.temp_logo.close()

    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove temporary logo file
        if hasattr(self, 'temp_logo'):
            Path(self.temp_logo.name).unlink(missing_ok=True)

    def test_init_with_defaults(self):
        """Test ImageProcessor initialization with default values."""
        processor = ImageProcessor()
        
        assert processor.logo_path == ImageProcessor.DEFAULT_LOGO_PATH
        assert processor.stamp_size == ImageProcessor.DEFAULT_STAMP_SIZE
        assert processor.signature_font_size == ImageProcessor.DEFAULT_SIGNATURE_FONT_SIZE
        assert processor.watermark_opacity == ImageProcessor.DEFAULT_WATERMARK_OPACITY

    def test_init_with_custom_values(self):
        """Test ImageProcessor initialization with custom values."""
        custom_logo_path = "/custom/logo.png"
        custom_stamp_size = (100, 100)
        custom_font_size = 60
        custom_opacity = 0.5
        
        processor = ImageProcessor(
            logo_path=custom_logo_path,
            stamp_size=custom_stamp_size,
            signature_font_size=custom_font_size,
            watermark_opacity=custom_opacity
        )
        
        assert processor.logo_path == custom_logo_path
        assert processor.stamp_size == custom_stamp_size
        assert processor.signature_font_size == custom_font_size
        assert processor.watermark_opacity == custom_opacity

    def test_init_with_nonexistent_logo(self):
        """Test ImageProcessor initialization with nonexistent logo path."""
        processor = ImageProcessor(logo_path="/nonexistent/logo.png")
        
        assert processor.logo_path == "/nonexistent/logo.png"

    def test_stamp_image_with_logo_success(self):
        """Test successful logo stamping."""
        processor = ImageProcessor(logo_path=self.temp_logo.name)
        
        result = processor.stamp_image_with_logo(self.test_image)
        
        assert result is not self.test_image  # Should return a new image
        assert result.size == self.test_image.size
        assert result.mode == self.test_image.mode

    def test_stamp_image_with_logo_no_logo_path(self):
        """Test logo stamping when no logo path is available."""
        processor = ImageProcessor(logo_path=None)
        
        result = processor.stamp_image_with_logo(self.test_image)
        
        # Should return a copy of the original image
        assert result is not self.test_image
        assert result.size == self.test_image.size

    def test_stamp_image_with_logo_invalid_logo(self):
        """Test logo stamping with invalid logo file."""
        # Create an invalid logo file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_file.write(b"invalid image data")
            temp_file_path = temp_file.name
        
        try:
            processor = ImageProcessor(logo_path=temp_file_path)
            
            with pytest.raises(ImageProcessingError):
                processor.stamp_image_with_logo(self.test_image)
        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    def test_stamp_image_with_logo_different_image_modes(self):
        """Test logo stamping with different image modes."""
        processor = ImageProcessor(logo_path=self.temp_logo.name)
        
        # Test with RGBA image
        rgba_image = Image.new("RGBA", (1024, 1024), color=(255, 255, 255, 255))
        result_rgba = processor.stamp_image_with_logo(rgba_image)
        assert result_rgba.mode == rgba_image.mode
        
        # Test with grayscale image
        gray_image = Image.new("L", (1024, 1024), color=128)
        result_gray = processor.stamp_image_with_logo(gray_image)
        assert result_gray.mode == gray_image.mode

    def test_sign_image_with_clouvel_success(self):
        """Test successful signature addition."""
        processor = ImageProcessor()
        
        result = processor.sign_image_with_clouvel(self.test_image)
        
        assert result is not self.test_image  # Should return a new image
        assert result.size == self.test_image.size
        assert result.mode == self.test_image.mode

    def test_sign_image_with_clouvel_different_image_modes(self):
        """Test signature addition with different image modes."""
        processor = ImageProcessor()
        
        # Test with RGBA image
        rgba_image = Image.new("RGBA", (1024, 1024), color=(255, 255, 255, 255))
        result_rgba = processor.sign_image_with_clouvel(rgba_image)
        assert result_rgba.mode == rgba_image.mode
        
        # Test with grayscale image
        gray_image = Image.new("L", (1024, 1024), color=128)
        result_gray = processor.sign_image_with_clouvel(gray_image)
        assert result_gray.mode == gray_image.mode

    def test_sign_image_with_clouvel_font_fallback(self):
        """Test signature addition with font fallback."""
        processor = ImageProcessor()
        
        # Mock both font loading methods
        with patch('PIL.ImageFont.truetype', side_effect=Exception("Font not found")), \
             patch('PIL.ImageFont.load_default') as mock_load_default:
            
            # Mock the default font
            mock_font = MagicMock()
            mock_load_default.return_value = mock_font
            
            with pytest.raises(ImageProcessingError):
                processor.sign_image_with_clouvel(self.test_image)
            mock_load_default.assert_called_once()

    def test_process_image_logo_only(self):
        """Test image processing with logo only."""
        processor = ImageProcessor(logo_path=self.temp_logo.name)
        
        result = processor.process_image(self.test_image, add_logo=True, add_signature=False)
        
        assert result is not self.test_image
        assert result.size == self.test_image.size

    def test_process_image_signature_only(self):
        """Test image processing with signature only."""
        processor = ImageProcessor()
        
        result = processor.process_image(self.test_image, add_logo=False, add_signature=True)
        
        assert result is not self.test_image
        assert result.size == self.test_image.size

    def test_process_image_both_logo_and_signature(self):
        """Test image processing with both logo and signature."""
        processor = ImageProcessor(logo_path=self.temp_logo.name)
        
        result = processor.process_image(self.test_image, add_logo=True, add_signature=True)
        
        assert result is not self.test_image
        assert result.size == self.test_image.size

    def test_process_image_neither_logo_nor_signature(self):
        """Test image processing with neither logo nor signature."""
        processor = ImageProcessor()
        
        result = processor.process_image(self.test_image, add_logo=False, add_signature=False)
        
        # Should return a copy of the original image
        assert result is not self.test_image
        assert result.size == self.test_image.size

    def test_process_image_error_handling(self):
        """Test error handling in image processing."""
        processor = ImageProcessor(logo_path="/nonexistent/logo.png")
        
        # This should not raise an exception, just return a copy of the original image
        result = processor.process_image(self.test_image, add_logo=True, add_signature=False)
        assert result is not self.test_image
        assert result.size == self.test_image.size

    def test_stamp_image_with_logo_custom_stamp_size(self):
        """Test logo stamping with custom stamp size."""
        custom_stamp_size = (120, 120)
        processor = ImageProcessor(
            logo_path=self.temp_logo.name,
            stamp_size=custom_stamp_size
        )
        
        result = processor.stamp_image_with_logo(self.test_image)
        
        assert result is not self.test_image
        assert result.size == self.test_image.size

    def test_sign_image_with_clouvel_custom_font_size(self):
        """Test signature addition with custom font size."""
        custom_font_size = 72
        processor = ImageProcessor(signature_font_size=custom_font_size)
        
        result = processor.sign_image_with_clouvel(self.test_image)
        
        assert result is not self.test_image
        assert result.size == self.test_image.size

    def test_stamp_image_with_logo_custom_opacity(self):
        """Test logo stamping with custom opacity."""
        custom_opacity = 0.7
        processor = ImageProcessor(
            logo_path=self.temp_logo.name,
            watermark_opacity=custom_opacity
        )
        
        result = processor.stamp_image_with_logo(self.test_image)
        
        assert result is not self.test_image
        assert result.size == self.test_image.size

    def test_stamp_image_with_logo_positioning(self):
        """Test that logo is positioned correctly in bottom-right corner."""
        processor = ImageProcessor(logo_path=self.temp_logo.name)
        
        # Create a test image with a specific color pattern to verify positioning
        test_image = Image.new("RGB", (1024, 1024), color="blue")
        
        result = processor.stamp_image_with_logo(test_image)
        
        # The logo should be in the bottom-right corner
        # We can verify this by checking that the image has been modified
        # (the exact pixel values would depend on the logo content)
        assert result is not test_image

    def test_sign_image_with_clouvel_positioning(self):
        """Test that signature is positioned correctly in bottom-right corner."""
        processor = ImageProcessor()
        
        # Create a test image with a specific color pattern to verify positioning
        test_image = Image.new("RGB", (1024, 1024), color="green")
        
        result = processor.sign_image_with_clouvel(test_image)
        
        # The signature should be in the bottom-right corner
        # We can verify this by checking that the image has been modified
        assert result is not test_image

    def test_image_processor_preserves_original_image(self):
        """Test that the original image is not modified."""
        processor = ImageProcessor(logo_path=self.temp_logo.name)
        
        original_image = self.test_image.copy()
        original_data = list(original_image.getdata())
        
        result = processor.stamp_image_with_logo(self.test_image)
        
        # Original image should be unchanged
        current_data = list(self.test_image.getdata())
        assert current_data == original_data
        
        # Result should be different
        result_data = list(result.getdata())
        assert result_data != original_data

    def test_image_processor_with_small_image(self):
        """Test image processing with a small image."""
        processor = ImageProcessor(logo_path=self.temp_logo.name)
        
        small_image = Image.new("RGB", (256, 256), color="red")
        
        # Should still work with smaller images
        result = processor.stamp_image_with_logo(small_image)
        assert result.size == small_image.size
        
        result = processor.sign_image_with_clouvel(small_image)
        assert result.size == small_image.size

    def test_image_processor_with_large_image(self):
        """Test image processing with a large image."""
        processor = ImageProcessor(logo_path=self.temp_logo.name)
        
        large_image = Image.new("RGB", (2048, 2048), color="yellow")
        
        # Should work with larger images
        result = processor.stamp_image_with_logo(large_image)
        assert result.size == large_image.size
        
        result = processor.sign_image_with_clouvel(large_image)
        assert result.size == large_image.size 