import os
import logging
from typing import Optional, Tuple
import httpx
from openai import OpenAI
from dotenv import load_dotenv
from app.clients.imgur_client import ImgurClient
from datetime import datetime
import base64

load_dotenv()

logger = logging.getLogger(__name__)

class ImageGenerator:
    """Handles image generation using DALL-E and storage using Imgur."""
    
    def __init__(self):
        """Initialize the image generator with OpenAI and Imgur clients."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set")
            
        self.client = OpenAI(api_key=api_key)
        self.imgur_client = ImgurClient()
        
    async def generate_image(self, prompt: str, size: str = "256x256", template_id: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate an image using DALL-E and store it both locally and on Imgur.
        
        Args:
            prompt: The text prompt for image generation
            size: The size of the image to generate (default: "256x256")
            template_id: Optional Zazzle template ID for naming the image file.
            
        Returns:
            Tuple containing (imgur_url, local_path)
            
        Raises:
            Exception: If image generation or upload fails
        """
        try:
            logger.info(f"Generating image for prompt: '{prompt}' with size: {size}")
            # Generate image using DALL-E
            response = self.client.images.generate(
                model="dall-e-2",
                prompt=prompt,
                size=size,
                n=1,
                response_format="b64_json"
            )
            
            # Get the base64 encoded image data directly
            image_data_b64 = response.data[0].b64_json
            if not image_data_b64:
                raise Exception("DALL-E did not return base64 image data.")
            
            image_data = base64.b64decode(image_data_b64)
            logger.info("Image data successfully retrieved from DALL-E response.")
                
            # Save locally and get the path with new naming convention
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename_prefix = f"{template_id}_{timestamp}" if template_id else f"dalle_{timestamp}"
            filename = f"{filename_prefix}_{size}.png"

            local_path = self.imgur_client.save_image_locally(image_data, filename, subdirectory="generated_products")
            logger.info(f"Image saved locally at: {local_path}")
            
            # Upload to Imgur
            imgur_url, _ = self.imgur_client.upload_image(local_path)
            logger.info(f"Image uploaded to Imgur. URL: {imgur_url}")
            
            return imgur_url, local_path
            
        except Exception as e:
            logger.error(f"Failed to generate or store image: {str(e)}")
            raise 