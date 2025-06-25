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

from PIL import Image, ImageDraw, ImageFont
import qrcode

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
    DEFAULT_STAMP_SIZE = (80, 80)
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

    def stamp_image_with_logo(self, image: Image.Image) -> Image.Image:
        """
        Add a circular logo stamp to the bottom-right corner of the image.

        Args:
            image (Image.Image): The input PIL image (expected 1024x1024).

        Returns:
            Image.Image: The stamped image (new object).

        Raises:
            ImageProcessingError: If logo loading or processing fails
        """
        if not self.logo_path or not Path(self.logo_path).exists():
            logger.warning("No valid logo path available, returning original image")
            return image.copy()

        try:
            # Copy image to avoid mutating input
            stamped = image.copy().convert("RGBA")
            width, height = stamped.size

            # Load the circular logo
            logo = Image.open(self.logo_path).convert("RGBA")

            # Extract stamp dimensions
            stamp_width, stamp_height = self.stamp_size

            # Position the stamp flush with the bottom-right (no margin)
            x = width - stamp_width
            y = height - stamp_height

            # Cut out the rectangle from the original image
            stamp_area = stamped.crop((x, y, x + stamp_width, y + stamp_height))

            # Resize logo to fit within the stamp area (with a little padding)
            logo_size = min(stamp_width, stamp_height) - 8  # 8px padding
            logo_resized = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

            # Create a new image for the logo overlay
            logo_overlay = Image.new("RGBA", (stamp_width, stamp_height), (0, 0, 0, 0))

            # Center the logo in the stamp area
            logo_x = (stamp_width - logo_size) // 2
            logo_y = (stamp_height - logo_size) // 2
            logo_overlay.paste(logo_resized, (logo_x, logo_y), logo_resized)

            # Apply transparency to make it watermark-like
            logo_overlay_data = logo_overlay.getdata()
            watermark_data = []
            for pixel in logo_overlay_data:
                if pixel[3] > 0:
                    watermark_data.append(
                        (
                            pixel[0],
                            pixel[1],
                            pixel[2],
                            int(pixel[3] * self.watermark_opacity),
                        )
                    )
                else:
                    watermark_data.append(pixel)
            watermark_overlay = Image.new("RGBA", (stamp_width, stamp_height))
            watermark_overlay.putdata(watermark_data)

            # Composite the watermark overlay onto the stamp area
            stamp_area_with_logo = Image.alpha_composite(stamp_area, watermark_overlay)

            # Paste the modified stamp area back into the original image
            stamped.paste(stamp_area_with_logo, (x, y))

            return stamped.convert(image.mode)

        except Exception as e:
            error_msg = f"Failed to stamp image with logo: {str(e)}"
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

            # Center the text in the signature area
            text_x = (signature_width - text_width) // 2
            text_y = (signature_height - text_height) // 2

            # Draw the signature in white
            draw.text(
                (text_x, text_y), signature, font=font, fill=(255, 255, 255, 255)
            )

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

    def logo_to_qr(self, image: Image.Image, url: str, logo_path: str = None) -> Image.Image:
        """
        Overlay a QR code (generated from the given URL) onto the image, using the logo as a mask.
        The QR code will only be visible where the logo is opaque (e.g., circular or custom logo shape).

        Args:
            image (Image.Image): The input PIL image (expected 1024x1024).
            url (str): The URL to encode as a QR code.
            logo_path (str, optional): Path to the logo file to use as a mask. Defaults to self.logo_path.

        Returns:
            Image.Image: The image with the QR code stamped using the logo mask.
        """
        logo_path = logo_path or self.logo_path
        if not logo_path or not Path(logo_path).exists():
            logger.warning("No valid logo path for QR mask, returning original image")
            return image.copy()

        try:
            # Generate QR code as a PIL image (black/white)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

            # Resize QR code to fit the stamp area
            stamp_width, stamp_height = self.stamp_size
            qr_img = qr_img.resize((stamp_width, stamp_height), Image.Resampling.LANCZOS)

            # Load the logo and use its alpha channel as a mask
            logo = Image.open(logo_path).convert("RGBA").resize((stamp_width, stamp_height), Image.Resampling.LANCZOS)
            mask = logo.split()[-1]  # Use alpha channel as mask

            # Composite the QR code using the logo mask
            qr_masked = Image.new("RGBA", (stamp_width, stamp_height), (0, 0, 0, 0))
            qr_masked.paste(qr_img, (0, 0), mask=mask)

            # Copy the original image and paste the masked QR code in the bottom-right
            stamped = image.copy().convert("RGBA")
            width, height = stamped.size
            x = width - stamp_width
            y = height - stamp_height

            # Cut out the area and composite the QR code
            stamp_area = stamped.crop((x, y, x + stamp_width, y + stamp_height))
            stamp_area_with_qr = Image.alpha_composite(stamp_area, qr_masked)
            stamped.paste(stamp_area_with_qr, (x, y))

            return stamped.convert(image.mode)
        except Exception as e:
            logger.error(f"Failed to overlay QR code with logo mask: {e}")
            return image.copy() 