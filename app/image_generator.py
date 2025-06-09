import os
import logging
from typing import Optional, Tuple, Dict, Any
import httpx
from openai import OpenAI
from openai.types.images_response import ImagesResponse
from dotenv import load_dotenv
from app.clients.imgur_client import ImgurClient
from datetime import datetime
import base64

load_dotenv()

logger = logging.getLogger(__name__)

class ImageGenerationError(Exception):
    """Custom exception for image generation errors."""
    pass

class ImageGenerator:
    """Handles image generation using DALL-E and storage using Imgur."""
    
    VALID_SIZES = {
        "dall-e-2": {"256x256", "512x512", "1024x1024"},
        "dall-e-3": {"1024x1024", "1024x1792", "1792x1024"}
    }
    DEFAULT_SIZE = {
        "dall-e-2": "256x256",
        "dall-e-3": "1024x1024"
    }
    VALID_MODELS = {"dall-e-2", "dall-e-3"}
    
    def __init__(self, model: str = "dall-e-2") -> None:
        """
        Initialize the image generator with OpenAI and Imgur clients.
        
        Args:
            model: The DALL-E model to use (default: "dall-e-2")
            
        Raises:
            ValueError: If OPENAI_API_KEY is not set or if model is invalid
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set")
            
        if model not in self.VALID_MODELS:
            raise ValueError(f"Invalid model. Must be one of: {', '.join(self.VALID_MODELS)}")
            
        self.client = OpenAI(api_key=api_key)
        self.imgur_client = ImgurClient()
        self.model = model
        
    async def generate_image(
        self, 
        prompt: str, 
        size: str = None, 
        template_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate an image using DALL-E and store it both locally and on Imgur.
        
        Args:
            prompt: The text prompt for image generation
            size: The size of the image to generate (default: None, which uses the model's default size)
            template_id: Optional Zazzle template ID for naming the image file
            
        Returns:
            Tuple containing (imgur_url, local_path)
            
        Raises:
            ImageGenerationError: If image generation or upload fails
            ValueError: If size is not valid for the selected model
        """
        if size is None:
            size = self.DEFAULT_SIZE[self.model]
        if size not in self.VALID_SIZES[self.model]:
            raise ValueError(f"Invalid size '{size}' for model '{self.model}'. Allowed: {', '.join(self.VALID_SIZES[self.model])}")
            
        try:
            logger.info(f"Generating image for prompt: '{prompt}' with size: {size}")
            
            # Consistent base prompt for the agent
            base_prompt = "You are a professional graphic designer and illustrator inspired by impressionist painters. Design an image to fill a 1.5 diameter round sticker. Integrate any text content seamlessly into the image, it should be creative, clear, or both. Ensure it isnt gibberish."
            full_prompt = f"{base_prompt} {prompt}"
            response = self.client.images.generate(
                model=self.model,
                prompt=full_prompt,
                size=size,
                n=1,
                response_format="b64_json"
            )
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
            
    def _generate_dalle_image(self, prompt: str, size: str) -> ImagesResponse:
        """
        Generate an image using DALL-E.
        
        Args:
            prompt: The text prompt for image generation
            size: The size of the image to generate
            
        Returns:
            ImagesResponse from DALL-E
            
        Raises:
            ImageGenerationError: If DALL-E API call fails
        """
        try:
            return self.client.images.generate(
                model="dall-e-2",
                prompt=prompt,
                size=size,
                n=1,
                response_format="b64_json"
            )
        except Exception as e:
            raise ImageGenerationError(f"DALL-E API call failed: {str(e)}") from e
            
    async def _process_and_store_image(
        self, 
        response: ImagesResponse, 
        template_id: Optional[str], 
        size: str
    ) -> Tuple[str, str]:
        """
        Process DALL-E response and store image locally and on Imgur.
        
        Args:
            response: DALL-E API response
            template_id: Optional template ID for file naming
            size: Image size for file naming
            
        Returns:
            Tuple containing (imgur_url, local_path)
            
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
            filename_prefix = f"{template_id}_{timestamp}" if template_id else f"dalle_{timestamp}"
            filename = f"{filename_prefix}_{size}.png"

            local_path = self.imgur_client.save_image_locally(
                image_data, 
                filename, 
                subdirectory="generated_products"
            )
            logger.info(f"Image saved locally at: {local_path}")
            
            # Upload to Imgur
            imgur_url, _ = self.imgur_client.upload_image(local_path)
            logger.info(f"Image uploaded to Imgur. URL: {imgur_url}")
            
            return imgur_url, local_path
            
        except Exception as e:
            raise ImageGenerationError(f"Failed to process or store image: {str(e)}") from e 