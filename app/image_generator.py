"""
Image generation module for the Zazzle Agent application.

This module provides functionality for generating images using DALL-E models
and storing them locally and on Imgur. It supports batch generation, prompt
versioning, and error handling for image generation workflows.

The module handles:
- Single image generation using DALL-E models
- Batch processing of multiple product ideas
- Local image storage and organization
- Imgur integration for image hosting
- Prompt versioning and management
- Error handling and logging
"""

import base64
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.images_response import ImagesResponse

from app.clients.imgur_client import ImgurClient
from app.models import ProductIdea, ProductInfo
from app.utils.logging_config import get_logger
from app.utils.openai_usage_tracker import track_openai_call, log_session_summary

load_dotenv()

logger = get_logger(__name__)

# Base prompts for different DALL-E models
IMAGE_GENERATION_BASE_PROMPTS = {
    "dall-e-2": {
        # "prompt": "You are a incredibly talented designer and illustrator with a passion for stickers. You are inspired by impressionist painters and the style of their paintings. Your designs must be beautiful and creative. Design an image optimized for a 1.5 inch diameter round image on Zazzle.",
        # version": "1.0.0"
        "prompt": "Create a square (1:1) image optimized for picture books and your 1024x1024 image size. Style and composition inspired by impressionist painters like Monet, Van Gogh, or Seurat, with precise brushwork and vibrant, light-filled colors. Emphasize nature. Text and any representations of text is not allowed. Craft a beautiful image based on the following description. ",
        "version": "1.0.1",
    },
    "dall-e-3": {
        # "prompt": "You are a incredibly talented designer and illustrator with a passion for stickers. You are inspired by impressionist painters and the style of their paintings. Your designs must be beautiful and creative. Design an image optimized for a 3 inch diameter round image on Zazzle.",
        # "version": "1.0.0"
        "prompt": "Create a square (1:1) image optimized for picture books and your 1024x1024 image size. Style and composition inspired by impressionist painters like Monet, Van Gogh, or Seurat, with precise brushwork and vibrant, light-filled colors. Emphasize nature. Text and any representations of text is not allowed. Craft a beautiful image based on the following description. ",
        "version": "1.0.1",
    },
}


class ImageGenerationError(Exception):
    """Exception raised for errors in image generation."""

    pass


class ImageGenerator:
    """
    Handles image generation using DALL-E and storage using Imgur.

    This class provides methods to generate images from prompts using DALL-E models,
    save them locally, upload to Imgur, and handle batch generation for multiple product ideas.

    The class supports:
    - Multiple DALL-E model versions (dall-e-2, dall-e-3)
    - Various image sizes per model
    - Local image storage with organized naming
    - Imgur integration for image hosting
    - Batch processing of product ideas
    - Error handling and logging

    Attributes:
        VALID_SIZES (Dict[str, set]): Allowed image sizes for each model
        DEFAULT_SIZE (Dict[str, str]): Default image size for each model
        VALID_MODELS (set): Supported DALL-E models
    """

    VALID_SIZES = {
        "dall-e-2": {"256x256", "512x512", "1024x1024"},
        "dall-e-3": {"1024x1024", "1024x1792", "1792x1024"},
    }
    DEFAULT_SIZE = {"dall-e-2": "256x256", "dall-e-3": "1024x1024"}
    VALID_MODELS = {"dall-e-2", "dall-e-3"}

    def __init__(self, model: str = "dall-e-2") -> None:
        """
        Initialize the image generator with OpenAI and Imgur clients.

        Args:
            model (str): The DALL-E model to use. Must be one of VALID_MODELS.
                Defaults to "dall-e-2".

        Raises:
            ValueError: If OPENAI_API_KEY is not set or if model is invalid
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set")

        if model not in self.VALID_MODELS:
            raise ValueError(
                f"Invalid model. Must be one of: {', '.join(self.VALID_MODELS)}"
            )

        self.client = OpenAI(api_key=api_key)
        self.imgur_client = ImgurClient()
        self.model = model
        logger.info(f"Initialized ImageGenerator with model: {model}")

    def get_prompt_info(self) -> Dict[str, str]:
        """
        Get the current prompt information for the model.

        Returns:
            Dict[str, str]: Dictionary containing the prompt and version for the current model.
        """
        return IMAGE_GENERATION_BASE_PROMPTS[self.model]

    @track_openai_call(model="dall-e-3", operation="image")
    def _generate_dalle_image(self, prompt: str, size: str) -> ImagesResponse:
        """
        Generate an image using DALL-E with tracking.

        Args:
            prompt (str): The text prompt for image generation
            size (str): The size of the image to generate

        Returns:
            ImagesResponse: Response from DALL-E API containing generated image data

        Raises:
            ImageGenerationError: If DALL-E API call fails
        """
        try:
            return self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size,
                n=1,
                response_format="b64_json",
            )
        except Exception as e:
            raise ImageGenerationError(f"DALL-E API call failed: {str(e)}") from e

    async def generate_image(
        self, prompt: str, size: Optional[str] = None, template_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate an image using DALL-E and store it both locally and on Imgur.

        Args:
            prompt (str): The text prompt for image generation
            size (str, optional): The size of the image to generate. If None, uses the
                model's default size.
            template_id (str, optional): Zazzle template ID for naming the image file

        Returns:
            Tuple[str, str]: Tuple containing (imgur_url, local_path)

        Raises:
            ImageGenerationError: If image generation or upload fails
            ValueError: If size is not valid for the selected model
        """
        if size is None:
            size = self.DEFAULT_SIZE[self.model]
        if size not in self.VALID_SIZES[self.model]:
            raise ValueError(
                f"Invalid size '{size}' for model '{self.model}'. Allowed: {', '.join(self.VALID_SIZES[self.model])}"
            )

        try:
            logger.info(
                f"Generating image for prompt: '{prompt}' with size: {size} with model: {self.model}"
            )

            # Get the base prompt for the model
            base_prompt = IMAGE_GENERATION_BASE_PROMPTS[self.model]["prompt"]
            full_prompt = f"{base_prompt} {prompt}"

            # Generate image with tracking
            response = self._generate_dalle_image(full_prompt, size)
            
            image_data_b64 = response.data[0].b64_json
            if not image_data_b64:
                raise ImageGenerationError("DALL-E did not return base64 image data.")
            logger.info("Image data successfully retrieved from DALL-E response.")

            # Process and store the image
            return await self._process_and_store_image(response, template_id, size)

        except Exception as e:
            error_msg = f"Failed to generate or store image: {str(e)}"
            logger.error(error_msg)
            raise ImageGenerationError(error_msg) from e

    async def _process_and_store_image(
        self, response: ImagesResponse, template_id: Optional[str], size: str
    ) -> Tuple[str, str]:
        """
        Process DALL-E response and store image locally and on Imgur.

        Args:
            response (ImagesResponse): DALL-E API response containing image data
            template_id (str, optional): Template ID for file naming
            size (str): Image size for file naming

        Returns:
            Tuple[str, str]: Tuple containing (imgur_url, local_path)

        Raises:
            ImageGenerationError: If image processing or storage fails
        """
        try:
            # Get the base64 encoded image data
            image_data_b64 = response.data[0].b64_json
            if not image_data_b64:
                raise ImageGenerationError("DALL-E did not return base64 image data.")

            image_data = base64.b64decode(image_data_b64)
            logger.info("Image data successfully retrieved from DALL-E response.")

            # Save locally with appropriate naming
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename_prefix = (
                f"{template_id}_{timestamp}" if template_id else f"dalle_{timestamp}"
            )
            filename = f"{filename_prefix}_{size}.png"

            local_path = self.imgur_client.save_image_locally(
                image_data, filename, subdirectory="generated_products"
            )
            logger.info(f"Image saved locally at: {local_path}")

            # Upload to Imgur
            imgur_url, _ = self.imgur_client.upload_image(local_path)
            logger.info(f"Image uploaded to Imgur. URL: {imgur_url}")

            return imgur_url, local_path

        except Exception as e:
            raise ImageGenerationError(
                f"Failed to process or store image: {str(e)}"
            ) from e

    async def generate_images_batch(
        self, product_ideas: List[ProductIdea]
    ) -> List[Union[ProductInfo, Dict[str, Any]]]:
        """
        Generate images for a batch of product ideas.

        Args:
            product_ideas (List[ProductIdea]): List of ProductIdea objects to process

        Returns:
            List[Union[ProductInfo, Dict[str, Any]]]: List of ProductInfo objects for successful
                generations, or error dictionaries for failed generations

        Raises:
            ImageGenerationError: If image generation fails for any product idea
        """
        results = []
        for idea in product_ideas:
            try:
                prompt = idea.image_description
                template_id = (
                    idea.design_instructions.get("template_id")
                    if idea.design_instructions
                    else None
                )

                if not prompt:
                    logger.warning("Skipping product idea with no image description")
                    continue

                # Generate image (mocked in tests)
                img_result = await self._generate_image(prompt, idea.model)
                imgur_url = img_result["url"]
                local_path = img_result["local_path"]

                # Create ProductInfo object
                product_info = ProductInfo(
                    product_id=f"product_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    name=idea.theme,
                    product_type="print",
                    zazzle_template_id=template_id,
                    zazzle_tracking_code="",
                    image_url=imgur_url,
                    product_url="",
                    theme=idea.theme,
                    model=idea.model,
                    prompt_version=idea.prompt_version,
                    reddit_context=idea.reddit_context,
                    design_instructions=idea.design_instructions,
                    image_local_path=local_path,
                )

                results.append(product_info)
                logger.info(f"Successfully generated image for product: {idea.theme}")

            except Exception as e:
                error_result = {
                    "error": str(e),
                    "product_idea": idea.theme,
                    "timestamp": datetime.now().isoformat(),
                }
                results.append(error_result)
                logger.error(f"Failed to generate image for product {idea.theme}: {e}")

        # Log session summary after batch processing
        log_session_summary()
        return results

    async def _generate_image(self, prompt: str, model: str) -> Dict[str, str]:
        """
        Generate a single image (for batch processing compatibility).

        Args:
            prompt (str): The image prompt
            model (str): The model to use

        Returns:
            Dict[str, str]: Dictionary with 'url' and 'local_path' keys
        """
        imgur_url, local_path = await self.generate_image(prompt)
        return {"url": imgur_url, "local_path": local_path}
