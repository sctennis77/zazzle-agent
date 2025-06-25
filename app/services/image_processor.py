"""
Image processing service module for the Zazzle Agent application.

This module provides functionality for processing and modifying images,
including adding watermarks, stamps, and signatures to generated images.

The module handles:
- Logo stamping with transparency effects
- Signature addition with custom text
- Image format conversion and preservation
- Error handling and logging
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import os
import numpy as np
import random

from PIL import Image, ImageDraw, ImageFont
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import ImageColorMask, SolidFillColorMask

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ImageProcessingError(Exception):
    """Exception raised for errors in image processing."""

    pass


class ImageProcessor:
    """
    Handles image processing operations including stamping and signing.

    This class provides methods to modify images by adding logos, watermarks,
    and signatures while preserving image quality and format.

    The class supports:
    - Logo stamping with configurable transparency
    - Signature addition with custom fonts and positioning
    - Multiple image format support
    - Error handling and logging

    Attributes:
        DEFAULT_LOGO_PATH (str): Default path to the logo file
        DEFAULT_STAMP_SIZE (Tuple[int, int]): Default size for logo stamps
        DEFAULT_SIGNATURE_FONT_SIZE (int): Default font size for signatures
        DEFAULT_WATERMARK_OPACITY (float): Default opacity for watermark effects
    """

    DEFAULT_LOGO_PATH = "frontend/src/assets/logo.png"
    DEFAULT_STAMP_SIZE = (100, 100)
    DEFAULT_SIGNATURE_FONT_SIZE = 48
    DEFAULT_WATERMARK_OPACITY = 0.3

    def __init__(
        self,
        logo_path: Optional[str] = None,
        stamp_size: Optional[Tuple[int, int]] = None,
        signature_font_size: Optional[int] = None,
        watermark_opacity: Optional[float] = None,
    ) -> None:
        """
        Initialize the image processor with configuration options.

        Args:
            logo_path (str, optional): Path to the logo file. If None, uses default path.
            stamp_size (Tuple[int, int], optional): Size for logo stamps. If None, uses default.
            signature_font_size (int, optional): Font size for signatures. If None, uses default.
            watermark_opacity (float, optional): Opacity for watermark effects. If None, uses default.

        Raises:
            ImageProcessingError: If logo file cannot be loaded
        """
        self.logo_path = logo_path or self.DEFAULT_LOGO_PATH
        self.stamp_size = stamp_size or self.DEFAULT_STAMP_SIZE
        self.signature_font_size = signature_font_size or self.DEFAULT_SIGNATURE_FONT_SIZE
        self.watermark_opacity = watermark_opacity or self.DEFAULT_WATERMARK_OPACITY

        # Validate logo path exists but don't change it
        if self.logo_path and not Path(self.logo_path).exists():
            logger.warning(f"Logo file not found at {self.logo_path}")

        logger.info(f"Initialized ImageProcessor with logo_path: {self.logo_path}")

    def stamp_image_with_logo(self, image: Image.Image, url: str = None, use_logo: bool = False) -> Image.Image:
        """
        Add a QR code stamp to the bottom-right corner of the image.
        Args:
            image (Image.Image): The input PIL image (expected 1024x1024).
            url (str, optional): The URL to encode as a QR code. If None, uses a default test URL.
            use_logo (bool, optional): Whether to use logo background (True) or simple background (False). Defaults to False.
        Returns:
            Image.Image: The stamped image (new object).
        """
        try:
            if url is None:
                url = "/redirect/test_image_20250625124000_1024x1024.png"
            
            # Generate the full-size QR code stamp based on mode
            if use_logo:
                qr_stamp_full = self.logo_to_qr(None, url)
            else:
                qr_stamp_full = self.simple_qr(None, url)
            
            # Resize to stamp size
            qr_stamp = qr_stamp_full.resize(self.stamp_size, Image.LANCZOS)
            
            # Add white border around the QR code stamp
            border_size = 3  # 3px white border
            bordered_stamp = Image.new('RGBA', 
                (self.stamp_size[0] + 2 * border_size, self.stamp_size[1] + 2 * border_size), 
                (255, 255, 255, 255))  # White background
            bordered_stamp.paste(qr_stamp, (border_size, border_size), qr_stamp)
            
            stamped = image.copy().convert('RGBA')
            img_width, img_height = stamped.size
            stamp_width, stamp_height = bordered_stamp.size
            x = img_width - stamp_width - 20
            y = img_height - stamp_height - 20
            stamped.paste(bordered_stamp, (x, y), bordered_stamp)
            return stamped
        except Exception as e:
            error_msg = f"Failed to stamp image with QR code: {str(e)}"
            logger.error(error_msg)
            raise ImageProcessingError(error_msg) from e

    def sign_image_with_clouvel(self, image: Image.Image) -> Image.Image:
        """
        Add a 'Clouvel '25' signature to the bottom-right corner of the image.

        Args:
            image (Image.Image): The input PIL image (expected 1024x1024).

        Returns:
            Image.Image: The signed image (new object).

        Raises:
            ImageProcessingError: If signature processing fails
        """
        try:
            # Copy image to avoid mutating input
            signed = image.copy().convert("RGBA")
            width, height = signed.size

            # Signature text
            signature = "Clouvel '25"

            # Try to use a script font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", self.signature_font_size)
            except Exception:
                font = ImageFont.load_default()

            # Calculate signature area (slightly bigger than before)
            margin = 32
            signature_width = 200  # Fixed width for signature area
            signature_height = 80  # Fixed height for signature area

            # Position the signature area in bottom-right
            x = width - signature_width - margin
            y = height - signature_height - margin

            # Cut out the rectangle from the original image
            signature_area = signed.crop(
                (x, y, x + signature_width, y + signature_height)
            )

            # Create a new image for the signature text
            signature_overlay = Image.new(
                "RGBA", (signature_width, signature_height), (0, 0, 0, 0)
            )
            draw = ImageDraw.Draw(signature_overlay)

            # Calculate text position within the signature area
            try:
                bbox = draw.textbbox((0, 0), signature, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            except AttributeError:
                text_width, text_height = font.getsize(signature)

            # Position centered at the bottom with some margin
            margin = 20
            x = (signature_width - text_width) // 2
            y = signature_height - text_height - margin
            
            # Signature color options
            signature_colors = [
                (40, 60, 200, 200),    # Sapphire blue
                (180, 40, 60, 200),   # Ruby red
                (40, 180, 100, 200),  # Emerald green
                (120, 60, 180, 200),  # Amethyst purple
                (230, 170, 40, 200),  # Topaz gold/orange
            ]
            signature_color = random.choice(signature_colors)
            draw.text((x, y), signature, font=font, fill=signature_color)

            # Composite the signature text onto the signature area
            signature_area_with_text = Image.alpha_composite(
                signature_area, signature_overlay
            )

            # Paste the modified signature area back into the original image
            signed.paste(signature_area_with_text, (x, y))

            return signed.convert(image.mode)

        except Exception as e:
            error_msg = f"Failed to sign image with Clouvel: {str(e)}"
            logger.error(error_msg)
            raise ImageProcessingError(error_msg) from e

    def process_image(
        self,
        image: Image.Image,
        add_logo: bool = True,
        add_signature: bool = False,
    ) -> Image.Image:
        """
        Process an image with optional logo stamping and signature addition.

        Args:
            image (Image.Image): The input PIL image.
            add_logo (bool): Whether to add logo stamp. Defaults to True.
            add_signature (bool): Whether to add signature. Defaults to False.

        Returns:
            Image.Image: The processed image.

        Raises:
            ImageProcessingError: If image processing fails
        """
        try:
            processed_image = image.copy()

            if add_logo:
                processed_image = self.stamp_image_with_logo(processed_image)

            if add_signature:
                processed_image = self.sign_image_with_clouvel(processed_image)

            return processed_image

        except Exception as e:
            error_msg = f"Failed to process image: {str(e)}"
            logger.error(error_msg)
            raise ImageProcessingError(error_msg) from e

    def simple_qr(self, image: Image.Image, url: str) -> Image.Image:
        """
        Generate a full-size QR code image (512x512) with a soft, clean, modern look.
        Uses a light blue/grey gradient, rounded corners, and partial opacity for modules.
        Ignores the input image size, always returns a 512x512 QR code image.
        """
        # Always use the manual method for maximum control
        return self._create_manual_styled_qr(url)

    def _create_manual_styled_qr(self, url: str) -> Image.Image:
        """Create a manually styled QR code with enhanced styling and Clouvel '25 signature for better appearance when reduced."""
        QR_SIZE = 512
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=3  # Slightly larger border for better margins
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Soft, very light blue/grey background
        bg_color = (235, 240, 250, 255)  # Very light blue-grey, fully opaque
        qr_img = Image.new('RGBA', (QR_SIZE, QR_SIZE), bg_color)
        draw = ImageDraw.Draw(qr_img)
        
        # Add subtle Clouvel '25 signature watermark
        try:
            # Create a temporary image for the signature
            signature_img = Image.new('RGBA', (QR_SIZE, QR_SIZE), (0, 0, 0, 0))
            signature_draw = ImageDraw.Draw(signature_img)
            
            # Use a nice font if available, otherwise fallback
            try:
                from PIL import ImageFont
                font_size = 48
                # Try Rock Salt font first
                font_paths = [
                    "fonts/RockSalt-Regular.ttf",  # Rock Salt font (Google Fonts)
                    "/System/Library/Fonts/Apple Chancery.ttf",  # Cursive style
                    "/System/Library/Fonts/Bradley Hand.ttc",    # Handwritten style
                    "/System/Library/Fonts/Chalkboard.ttc",      # Chalkboard style
                    "/System/Library/Fonts/Arial.ttf"           # Fallback
                ]
                font = None
                for font_path in font_paths:
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        break
                    except:
                        continue
                if font is None:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Signature text and position (bottom-right corner)
            signature_text = "Clouvel '25"
            text_bbox = signature_draw.textbbox((0, 0), signature_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Position centered at the bottom with some margin
            margin = 20
            x = (QR_SIZE - text_width) // 2
            y = QR_SIZE - text_height - margin
            
            # Signature color options
            signature_colors = [
                (40, 60, 200, 200),    # Sapphire blue
                (180, 40, 60, 200),   # Ruby red
                (40, 180, 100, 200),  # Emerald green
                (120, 60, 180, 200),  # Amethyst purple
                (230, 170, 40, 200),  # Topaz gold/orange
            ]
            signature_color = random.choice(signature_colors)
            signature_draw.text((x, y), signature_text, fill=signature_color, font=font)
            
            # Composite the signature onto the background
            qr_img = Image.alpha_composite(qr_img, signature_img)
            
        except Exception as e:
            logger.warning(f"Could not add signature watermark: {e}")
            # Continue without signature if there's an error
        
        # Enhanced blue/grey gradient for better readability when reduced
        grad_start = np.array([70, 100, 150])   # Darker blue-grey
        grad_end = np.array([110, 140, 190])    # Lighter blue-grey
        alpha = 255  # Fully opaque for maximum contrast and readability
        
        qr_matrix = qr.get_matrix()
        modules_count = len(qr_matrix)
        module_size = QR_SIZE // modules_count
        
        # Larger corner radius for smoother appearance when scaled
        corner_radius = max(6, module_size // 2)
        
        for y in range(modules_count):
            for x in range(modules_count):
                if qr_matrix[y][x]:
                    # Calculate gradient based on position
                    t = (y + x) / (2 * (modules_count - 1))  # Diagonal gradient
                    color = tuple((grad_start * (1 - t) + grad_end * t).astype(int))
                    
                    # Module coordinates
                    left = x * module_size
                    top = y * module_size
                    right = (x + 1) * module_size
                    bottom = (y + 1) * module_size
                    
                    # Create a slightly larger area for the halo effect
                    halo_size = module_size + 4
                    halo_left = left - 2
                    halo_top = top - 2
                    
                    # Draw white halo/glow first
                    halo_mask = Image.new('L', (halo_size, halo_size), 0)
                    halo_draw = ImageDraw.Draw(halo_mask)
                    halo_draw.rounded_rectangle(
                        [0, 0, halo_size, halo_size], 
                        radius=corner_radius + 2, 
                        fill=180  # Semi-transparent white
                    )
                    
                    # Create the halo image
                    halo_img = Image.new('RGBA', (halo_size, halo_size), (255, 255, 255, 180))
                    halo_img.putalpha(halo_mask)
                    
                    # Paste the halo
                    qr_img.paste(halo_img, (halo_left, halo_top), halo_img)
                    
                    # Draw the main module with rounded corners
                    mask = Image.new('L', (module_size, module_size), 0)
                    mask_draw = ImageDraw.Draw(mask)
                    mask_draw.rounded_rectangle(
                        [0, 0, module_size, module_size], 
                        radius=corner_radius, 
                        fill=255
                    )
                    
                    # Create the colored module
                    module_img = Image.new('RGBA', (module_size, module_size), color + (alpha,))
                    module_img.putalpha(mask)
                    
                    # Paste the main module
                    qr_img.paste(module_img, (left, top), module_img)
        
        return qr_img

    def logo_to_qr(self, image: Image.Image, url: str, logo_path: str = None) -> Image.Image:
        """
        Generate a full-size QR code image (512x512) with the prepped background and advanced styling.
        Ignores the input image size, always returns a 512x512 QR code image.
        """
        try:
            prepped_bg_path = os.path.join(os.path.dirname(__file__), '../../scripts/logo_qr_background.png')
            use_prepped_bg = os.path.exists(prepped_bg_path)
            QR_SIZE = 512
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=2
            )
            qr.add_data(url)
            qr.make(fit=True)
            qr_matrix = qr.get_matrix()
            modules_count = len(qr_matrix)
            module_size = QR_SIZE // modules_count
            if use_prepped_bg:
                logo_bg = Image.open(prepped_bg_path).convert('RGBA').resize((QR_SIZE, QR_SIZE), Image.LANCZOS)
            else:
                logo_bg = Image.open(self.logo_path).convert('RGBA').resize((QR_SIZE, QR_SIZE), Image.LANCZOS)
            qr_img = Image.new('RGBA', (QR_SIZE, QR_SIZE), (0, 0, 0, 0))
            draw = ImageDraw.Draw(qr_img)
            grad_start = np.array([10, 15, 30])
            grad_end = np.array([20, 30, 60])
            alpha = 255
            for y in range(modules_count):
                for x in range(modules_count):
                    if qr_matrix[y][x]:
                        t = y / (modules_count - 1)
                        color = tuple((grad_start * (1 - t) + grad_end * t).astype(int))
                        rect = [x * module_size, y * module_size, (x + 1) * module_size, (y + 1) * module_size]
                        draw.rectangle(rect, fill=color + (alpha,))
            final_img = logo_bg.copy()
            final_img.paste(qr_img, (0, 0), qr_img)
            return final_img
        except Exception as e:
            logger.error(f"Error creating advanced QR code stamp: {e}")
            raise ImageProcessingError(f"Failed to create advanced QR code stamp: {e}")

    def create_qr_variants(self, image: Image.Image, url: str, logo_path: str = None) -> dict:
        """
        Create multiple QR code variants for testing and comparison.
        
        Args:
            image (Image.Image): The input PIL image.
            url (str): The URL to encode as a QR code.
            logo_path (str, optional): Path to the logo file.
            
        Returns:
            dict: Dictionary containing different QR code variants.
        """
        variants = {}
        
        try:
            # Variant 1: Logo embedded in center (current implementation)
            variants['embedded_logo'] = self.logo_to_qr(image, url, logo_path)
            
            # Variant 2: Simple QR code with logo overlay
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=2
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # Create simple QR code
            simple_qr = qr.make_image(fill_color="black", back_color="white")
            simple_qr = simple_qr.resize(self.stamp_size, Image.Resampling.LANCZOS)
            
            # Load and resize logo for overlay
            logo_path = logo_path or self.logo_path
            logo = Image.open(logo_path).convert("RGBA")
            logo_size = (self.stamp_size[0] // 4, self.stamp_size[1] // 4)  # 1/4 of QR size
            logo = logo.resize(logo_size, Image.Resampling.LANCZOS)
            
            # Create circular mask for logo
            mask = Image.new('L', logo_size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, logo_size[0], logo_size[1]), fill=255)
            
            # Apply mask to logo
            logo.putalpha(mask)
            
            # Calculate center position for logo
            qr_center_x = simple_qr.size[0] // 2 - logo_size[0] // 2
            qr_center_y = simple_qr.size[1] // 2 - logo_size[1] // 2
            
            # Create result image
            result_image = image.copy()
            qr_with_logo = simple_qr.copy()
            qr_with_logo.paste(logo, (qr_center_x, qr_center_y), logo)
            
            # Position in bottom-right
            img_width, img_height = result_image.size
            qr_width, qr_height = qr_with_logo.size
            x = img_width - qr_width - 20
            y = img_height - qr_height - 20
            
            result_image.paste(qr_with_logo, (x, y))
            variants['overlay_logo'] = result_image
            
            return variants
            
        except Exception as e:
            logger.error(f"Error creating QR variants: {e}")
            raise ImageProcessingError(f"Failed to create QR variants: {e}")

# --- TEST FUNCTION FOR INDEPENDENT QR STAMP GENERATION ---
if __name__ == "__main__":
    from PIL import Image
    import numpy as np
    # Load the prepped background
    bg_path = os.path.join(os.path.dirname(__file__), '../../scripts/logo_qr_background.png')
    logo_bg = Image.open(bg_path).convert('RGBA').resize((512, 512), Image.LANCZOS)
    
    # Generate QR code matrix
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2
    )
    test_url = "/redirect/test_image_20250625124000_1024x1024.png"
    qr.add_data(test_url)
    qr.make(fit=True)
    qr_matrix = qr.get_matrix()
    modules_count = len(qr_matrix)
    module_size = 512 // modules_count
    
    # Create QR code image with gradient and partial transparency
    qr_img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(qr_img)
    grad_start = np.array([10, 15, 30])   # POC dark navy
    grad_end = np.array([20, 30, 60])    # POC dark blue
    alpha = 255  # Fully opaque as in POC
    for y in range(modules_count):
        for x in range(modules_count):
            if qr_matrix[y][x]:
                t = y / (modules_count - 1)
                color = tuple((grad_start * (1 - t) + grad_end * t).astype(int))
                rect = [x * module_size, y * module_size, (x + 1) * module_size, (y + 1) * module_size]
                draw.rectangle(rect, fill=color + (alpha,))
    
    # Composite QR code over the prepped background
    final_img = logo_bg.copy()
    final_img.paste(qr_img, (0, 0), qr_img)
    final_img.save("test_qr_stamp_output.png")
    print("✅ Saved test_qr_stamp_output.png with full-size QR code and prepped background.") 