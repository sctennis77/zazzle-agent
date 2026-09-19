import base64
import io
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from openai import AsyncOpenAI
from openai.types.images_response import ImagesResponse
from PIL import Image

from app.clients.imgur_client import ImgurClient
from app.services.image_processor import ImageProcessor
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_IMAGE_MODEL = "gpt-image-2"
LEGACY_DALLE_MODELS = {"dall-e-2", "dall-e-3"}
# gpt-image-1 / 1.5 remain callable until their shutdown dates, but new
# generations default to gpt-image-2.
GPT_IMAGE_MODELS = {
    "gpt-image-1",
    "gpt-image-1-mini",
    "gpt-image-1.5",
    "gpt-image-2",
    "gpt-image-2.5-sunburst",
    "gpt-image-2.5-flare",
}

# App-level quality values stored in the DB / shown in the UI.
APP_QUALITY_STANDARD = "standard"
APP_QUALITY_HD = "hd"

# GPT Image models rejected DALL·E's quality, style, and response_format fields.
QUALITY_TO_API = {
    "standard": "medium",
    "low": "low",
    "medium": "medium",
    "hd": "high",
    "high": "high",
    "xhigh": "high",
    "max": "high",
    "auto": "auto",
}
API_QUALITY_TO_APP = {
    "low": APP_QUALITY_STANDARD,
    "medium": APP_QUALITY_STANDARD,
    "high": APP_QUALITY_HD,
    "xhigh": APP_QUALITY_HD,
    "max": APP_QUALITY_HD,
    "auto": APP_QUALITY_STANDARD,
    "standard": APP_QUALITY_STANDARD,
    "hd": APP_QUALITY_HD,
}
SIZE_ALIASES = {
    "256x256": "1024x1024",
    "512x512": "1024x1024",
    "1024x1792": "1024x1536",
    "1792x1024": "1536x1024",
}
GPT_IMAGE_SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}

ILLUSTRATION_PROMPT = (
    "Create a square (1:1) image designed for clear, engaging visual storytelling on a webpage. "
    "and your 1024x1024 image size. Create a beautiful illustration based on the following scene "
    "description. Use a combined impasto and pointillism style, inspired by painters like Van Gogh "
    "and Seurat. Focus on visible brushstrokes, rich texture, and vibrant, light-filled color with "
    "a strong emphasis on nature. Highlight mood, setting, and symbolic details rather than "
    "realism. Do not include any text or representations of text."
)

# Base prompts for image models. Legacy DALL·E keys are kept so stored products
# and existing tests still resolve prompt version metadata.
IMAGE_GENERATION_BASE_PROMPTS = {
    "dall-e-2": {
        "prompt": "Create a square (1:1) image optimized for picture books and your 1024x1024 image size. Style and composition inspired by impressionist painters like Monet, Van Gogh, or Seurat, with precise brushwork and vibrant, light-filled colors. Emphasize nature. Text and any representations of text is not allowed. Craft a beautiful image based on the following description. ",
        "version": "1.0.1",
    },
    "dall-e-3": {
        "prompt": ILLUSTRATION_PROMPT,
        "version": "1.0.1",
    },
    "gpt-image-1": {
        "prompt": ILLUSTRATION_PROMPT,
        "version": "1.1.0",
    },
    "gpt-image-1.5": {
        "prompt": ILLUSTRATION_PROMPT,
        "version": "1.1.0",
    },
    "gpt-image-2": {
        "prompt": ILLUSTRATION_PROMPT,
        "version": "1.1.0",
    },
}


def get_default_image_model() -> str:
    """Return the configured GPT Image model, defaulting to gpt-image-2."""
    return os.getenv("OPENAI_IMAGE_MODEL", DEFAULT_IMAGE_MODEL)


def normalize_app_quality(quality: Optional[str]) -> str:
    """Map caller quality values onto the stored standard/hd vocabulary."""
    if not quality:
        return APP_QUALITY_STANDARD
    mapped = API_QUALITY_TO_APP.get(quality.lower())
    if mapped is None:
        raise ValueError(
            f"Invalid quality '{quality}'. Must be one of: {', '.join(sorted(QUALITY_TO_API))}"
        )
    return mapped


def to_api_quality(quality: str) -> str:
    """Map stored or caller quality values onto the GPT Image API vocabulary."""
    mapped = QUALITY_TO_API.get(quality.lower())
    if mapped is None:
        raise ValueError(
            f"Invalid quality '{quality}'. Must be one of: {', '.join(sorted(QUALITY_TO_API))}"
        )
    return mapped


def resolve_image_model(model: str) -> str:
    """Map retired DALL·E model IDs onto the current GPT Image model."""
    if model in LEGACY_DALLE_MODELS:
        resolved = get_default_image_model()
        logger.warning(
            "Image model '%s' was retired from the OpenAI Images API; using '%s' instead",
            model,
            resolved,
        )
        return resolved
    if model in GPT_IMAGE_MODELS or model.startswith("gpt-image-"):
        return model
    raise ValueError(
        f"Invalid model '{model}'. Must be a GPT Image model or a legacy DALL·E alias"
    )


def resolve_image_size(size: str) -> str:
    """Map DALL·E sizes onto GPT Image sizes."""
    mapped = SIZE_ALIASES.get(size, size)
    if mapped not in GPT_IMAGE_SIZES:
        raise ValueError(
            f"Invalid size '{size}'. Allowed: {', '.join(sorted(GPT_IMAGE_SIZES | set(SIZE_ALIASES)))}"
        )
    return mapped


class ImageGenerationError(Exception):
    """Exception raised for errors in image generation."""

    pass


class AsyncImageGenerator:
    """
    Asynchronous image generator using the OpenAI Images API and Imgur.

    DALL·E 2/3 were removed from the API in May 2026. Requests now use GPT Image
    models, which always return base64 (`b64_json`) and reject `response_format`
    and `style`.
    """

    VALID_SIZES = {
        "dall-e-2": {"256x256", "512x512", "1024x1024"},
        "dall-e-3": {"1024x1024", "1024x1792", "1792x1024"},
        **{model: set(GPT_IMAGE_SIZES) for model in GPT_IMAGE_MODELS},
    }
    DEFAULT_SIZE = {
        "dall-e-2": "1024x1024",
        "dall-e-3": "1024x1024",
        **{model: "1024x1024" for model in GPT_IMAGE_MODELS},
    }
    VALID_MODELS = LEGACY_DALLE_MODELS | GPT_IMAGE_MODELS
    VALID_QUALITIES = set(QUALITY_TO_API)
    DEFAULT_QUALITY = APP_QUALITY_STANDARD

    def __init__(
        self,
        model: Optional[str] = None,
        style: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set")
        requested_model = model or get_default_image_model()
        self.requested_model = requested_model
        self.model = resolve_image_model(requested_model)
        self.client = AsyncOpenAI(api_key=api_key)
        self.imgur_client = ImgurClient()
        self.image_processor = ImageProcessor()
        # GPT Image models do not support DALL·E's style parameter.
        if style:
            logger.info(
                "Ignoring unsupported style=%s for GPT Image model %s",
                style,
                self.model,
            )
        self.style = None
        self.quality = normalize_app_quality(quality)

        logger.info(
            "Initialized AsyncImageGenerator with model: %s (requested: %s), quality: %s",
            self.model,
            self.requested_model,
            self.quality,
        )

    def get_prompt_info(self) -> Dict[str, str]:
        if self.requested_model in IMAGE_GENERATION_BASE_PROMPTS:
            return IMAGE_GENERATION_BASE_PROMPTS[self.requested_model]
        if self.model in IMAGE_GENERATION_BASE_PROMPTS:
            return IMAGE_GENERATION_BASE_PROMPTS[self.model]
        return IMAGE_GENERATION_BASE_PROMPTS["dall-e-3"]

    def _build_generate_kwargs(
        self, prompt: str, size: str, quality: str
    ) -> Dict[str, Any]:
        """Build Images API kwargs for the current GPT Image contract."""
        return {
            "model": self.model,
            "prompt": prompt,
            "size": resolve_image_size(size),
            "n": 1,
            "quality": to_api_quality(quality),
            "output_format": "png",
        }

    async def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        template_id: Optional[str] = None,
        stamp_image: bool = True,
        quality: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Generate an image using the OpenAI Images API and store it locally and on Imgur.
        """
        if size is None:
            size = self.DEFAULT_SIZE.get(self.requested_model) or self.DEFAULT_SIZE.get(
                self.model, "1024x1024"
            )
        api_size = resolve_image_size(size)
        image_quality = (
            normalize_app_quality(quality) if quality is not None else self.quality
        )

        try:
            logger.info(
                "[Async] Generating image for prompt: '%s' with size: %s (api: %s), quality: %s, model: %s",
                prompt,
                size,
                api_size,
                image_quality,
                self.model,
            )
            base_prompt = self.get_prompt_info()["prompt"]
            full_prompt = f"{base_prompt} {prompt}"
            generate_kwargs = self._build_generate_kwargs(
                full_prompt, size, image_quality
            )
            response = await self.client.images.generate(**generate_kwargs)
            if not response.data:
                raise ImageGenerationError(
                    "Image API returned no data. GPT Image models reject response_format "
                    "and always return b64_json."
                )
            image_data_b64 = response.data[0].b64_json
            if not image_data_b64:
                raise ImageGenerationError("Image API did not return base64 image data.")
            logger.info("[Async] Image data successfully retrieved from Image API response.")
            return await self._process_and_store_image(
                response,
                template_id,
                api_size,
                stamp_image=stamp_image,
                quality=image_quality,
            )
        except ImageGenerationError:
            raise
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
        Process Image API response and store image locally and on Imgur.
        """
        try:
            image_data_b64 = response.data[0].b64_json
            if not image_data_b64:
                raise ImageGenerationError("Image API did not return base64 image data.")
            image_data = base64.b64decode(image_data_b64)
            logger.info("[Async] Image data successfully retrieved from Image API response.")
            image = Image.open(io.BytesIO(image_data))
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename_prefix = (
                f"{template_id}_{timestamp}" if template_id else f"gptimage_{timestamp}"
            )
            filename = f"{filename_prefix}_{size}.png"
            if stamp_image:
                stamped_filename = f"stamped_{filename}"
                if qr_url:
                    stamp_url = qr_url
                elif product_idea and product_idea.get("affiliate_link"):
                    stamp_url = product_idea["affiliate_link"]
                else:
                    from app.config import BASE_URL

                    stamp_url = f"{BASE_URL}/redirect/{stamped_filename}"
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
