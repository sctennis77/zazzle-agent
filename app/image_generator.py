import os
import logging
from typing import Optional, Tuple
import httpx
from openai import OpenAI
from dotenv import load_dotenv
from app.clients.imgur_client import ImgurClient

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
        
    async def generate_image(self, prompt: str, size: str = "256x256") -> Tuple[str, str]:
        """
        Generate an image using DALL-E and store it both locally and on Imgur.
        
        Args:
            prompt: The text prompt for image generation
            size: The size of the image to generate (default: "256x256")
            
        Returns:
            Tuple containing (imgur_url, local_path)
            
        Raises:
            Exception: If image generation or upload fails
        """
        try:
            # Generate image using DALL-E
            response = self.client.images.generate(
                model="dall-e-2",
                prompt=prompt,
                size=size,
                n=1
            )
            
            # Get the image URL from DALL-E
            image_url = response.data[0].url
            
            # Download the image
            async with httpx.AsyncClient() as client:
                image_response = await client.get(image_url)
                image_data = image_response.content
                
            # Save locally and get the path
            filename = f"dalle_{hash(prompt)}_{size}.png"
            local_path = self.imgur_client.save_image_locally(image_data, filename)
            
            # Upload to Imgur
            imgur_url, _ = self.imgur_client.upload_image(local_path)
            
            return imgur_url, local_path
            
        except Exception as e:
            logger.error(f"Failed to generate or store image: {str(e)}")
            raise 