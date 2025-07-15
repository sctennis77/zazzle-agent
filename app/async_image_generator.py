import base64
import io
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from openai import AsyncOpenAI
from openai.types.images_response import ImagesResponse
from PIL import Image

from app.clients.imgur_client import ImgurClient
from app.models import ProductIdea, ProductInfo
from app.services.image_processor import ImageProcessor
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Base prompts for different DALL-E models
IMAGE_GENERATION_BASE_PROMPTS = {
    "dall-e-2": {
        "prompt": "Create a square (1:1) image optimized for picture books and your 1024x1024 image size. Style and composition inspired by impressionist painters like Monet, Van Gogh, or Seurat, with precise brushwork and vibrant, light-filled colors. Emphasize nature. Text and any representations of text is not allowed. Craft a beautiful image based on the following description. ",
        "version": "1.0.1",
    },
    "dall-e-3": {
        "prompt": "Create a square (1:1) image designed for clear, engaging visual storytelling on a webpage. and your 1024x1024 image size. Create a beautiful illustration based on the following scene description. Use a combined impasto and pointillism style, inspired by painters like Van Gogh and Seurat. Focus on visible brushstrokes, rich texture, and vibrant, light-filled color with a strong emphasis on nature. Highlight mood, setting, and symbolic details rather than realism. Do not include any text or representations of text.",
        "version": "1.0.1",
    },
}


class ImageGenerationError(Exception):
    """Exception raised for errors in image generation."""

    pass


class AsyncImageGenerator:
    """
    Asynchronous image generator using DALL-E and Imgur, matching ImageGenerator's interface.
    """

    VALID_SIZES = {
        "dall-e-2": {"256x256", "512x512", "1024x1024"},
        "dall-e-3": {"1024x1024", "1024x1792", "1792x1024"},
    }
    DEFAULT_SIZE = {"dall-e-2": "256x256", "dall-e-3": "1024x1024"}
    VALID_MODELS = {"dall-e-2", "dall-e-3"}
    DEFAULT_STYLES = {"dall-e-3": "vivid", "dall-e-2": "vivid"}
    VALID_QUALITIES = {"standard", "hd"}
    DEFAULT_QUALITY = "standard"

    def __init__(
        self,
        model: str = "dall-e-3",
        style: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set")
        if model not in self.VALID_MODELS:
            raise ValueError(
                f"Invalid model. Must be one of: {', '.join(self.VALID_MODELS)}"
            )
        self.client = AsyncOpenAI(api_key=api_key)
        self.imgur_client = ImgurClient()
        self.image_processor = ImageProcessor()
        self.model = model
        if model == "dall-e-2":
            self.style = style or self.DEFAULT_STYLES[model]
        else:
            self.style = None

        # Quality is only supported for DALL-E 3
        if quality and model == "dall-e-2":
            logger.warning("Quality parameter is not supported for DALL-E 2, ignoring")
            self.quality = self.DEFAULT_QUALITY
        else:
            self.quality = quality or self.DEFAULT_QUALITY
            if self.quality not in self.VALID_QUALITIES:
                raise ValueError(
                    f"Invalid quality. Must be one of: {', '.join(self.VALID_QUALITIES)}"
                )

        logger.info(
            f"Initialized AsyncImageGenerator with model: {model}, style: {self.style}, quality: {self.quality}"
        )

    def get_prompt_info(self) -> Dict[str, str]:
        return IMAGE_GENERATION_BASE_PROMPTS[self.model]

    async def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        template_id: Optional[str] = None,
        stamp_image: bool = True,
        quality: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Generate an image using DALL-E asynchronously and store it both locally and on Imgur.
        """
        if size is None:
            size = self.DEFAULT_SIZE[self.model]
        if size not in self.VALID_SIZES[self.model]:
            raise ValueError(
                f"Invalid size '{size}' for model '{self.model}'. Allowed: {', '.join(self.VALID_SIZES[self.model])}"
            )
        # Use quality parameter if provided, otherwise use instance default
        image_quality = quality if quality is not None else self.quality

        # Validate quality for the model
        if image_quality not in self.VALID_QUALITIES:
            raise ValueError(
                f"Invalid quality '{image_quality}'. Must be one of: {', '.join(self.VALID_QUALITIES)}"
            )

        try:
            logger.info(
                f"[Async] Generating image for prompt: '{prompt}' with size: {size}, quality: {image_quality}, model: {self.model}"
            )
            base_prompt = IMAGE_GENERATION_BASE_PROMPTS[self.model]["prompt"]
            full_prompt = f"{base_prompt} {prompt}"
            if self.model == "dall-e-3":
                response = await self.client.images.generate(
                    model=self.model,
                    prompt=full_prompt,
                    size=size,
                    n=1,
                    style="vivid",
                    quality=image_quality,
                    response_format="b64_json",
                )
            else:
                # DALL-E 2 doesn't support quality parameter
                response = await self.client.images.generate(
                    model=self.model,
                    prompt=full_prompt,
                    size=size,
                    n=1,
                    style=self.style,
                    response_format="b64_json",
                )
            image_data_b64 = response.data[0].b64_json
            if not image_data_b64:
                raise ImageGenerationError("DALL-E did not return base64 image data.")
            logger.info(
                "[Async] Image data successfully retrieved from DALL-E response."
            )
            return await self._process_and_store_image(
                response,
                template_id,
                size,
                stamp_image=stamp_image,
                quality=image_quality,
            )
        except Exception as e:
            error_msg = f"[Async] Failed to generate or store image: {str(e)}"
            logger.error(error_msg)
            raise ImageGenerationError(error_msg) from e

    async def _process_and_store_image(
        self,
        response: ImagesResponse,
        template_id: Optional[str],
        size: str,
        stamp_image: bool = True,
        qr_url: Optional[str] = None,
        product_idea: Optional[dict] = None,
        quality: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Process DALL-E response and store image locally and on Imgur.
        """
        try:
            image_data_b64 = response.data[0].b64_json
            if not image_data_b64:
                raise ImageGenerationError("DALL-E did not return base64 image data.")
            image_data = base64.b64decode(image_data_b64)
            logger.info(
                "[Async] Image data successfully retrieved from DALL-E response."
            )
            image = Image.open(io.BytesIO(image_data))
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename_prefix = (
                f"{template_id}_{timestamp}" if template_id else f"dalle_{timestamp}"
            )
            filename = f"{filename_prefix}_{size}.png"
            if stamp_image:
                stamped_filename = f"stamped_{filename}"
                if qr_url:
                    stamp_url = qr_url
                elif product_idea and product_idea.get("affiliate_link"):
                    stamp_url = product_idea["affiliate_link"]
                else:
                    stamp_url = f"/redirect/{stamped_filename}"
                stamped_image = self.image_processor.stamp_image_with_logo(
                    image, stamp_url
                )
                stamped_output_bytes = io.BytesIO()
                stamped_image.save(stamped_output_bytes, format="PNG")
                stamped_output_bytes.seek(0)
                stamped_image_data = stamped_output_bytes.read()
                stamped_local_path = self.imgur_client.save_image_locally(
                    stamped_image_data,
                    stamped_filename,
                    subdirectory="generated_products",
                )
                stamped_imgur_url, _ = self.imgur_client.upload_image(
                    stamped_local_path
                )
                logger.info(
                    f"[Async] Stamped image uploaded to Imgur. URL: {stamped_imgur_url}"
                )
                return stamped_imgur_url, stamped_local_path
            else:
                output_bytes = io.BytesIO()
                image.save(output_bytes, format="PNG")
                output_bytes.seek(0)
                processed_image_data = output_bytes.read()
                local_path = self.imgur_client.save_image_locally(
                    processed_image_data, filename, subdirectory="generated_products"
                )
                logger.info(f"[Async] Image saved locally at: {local_path}")
                imgur_url, _ = self.imgur_client.upload_image(local_path)
                logger.info(f"[Async] Image uploaded to Imgur. URL: {imgur_url}")
                return imgur_url, local_path
        except Exception as e:
            raise ImageGenerationError(
                f"[Async] Failed to process or store image: {str(e)}"
            ) from e
