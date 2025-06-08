import os
import logging
from typing import Dict, Optional, Tuple
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ImgurClient:
    """Client for interacting with the Imgur API."""
    
    def __init__(self):
        """Initialize the Imgur client with credentials from environment variables."""
        self.client_id = os.getenv('IMGUR_CLIENT_ID')
        self.client_secret = os.getenv('IMGUR_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            logger.error("Imgur credentials not found in environment variables")
            raise ValueError("IMGUR_CLIENT_ID and IMGUR_CLIENT_SECRET must be set")
            
        self.base_url = "https://api.imgur.com/3"
        self.headers = {
            'Authorization': f'Client-ID {self.client_id}'
        }
        
    def upload_image(self, image_path: str) -> Tuple[str, str]:
        """
        Upload an image to Imgur and return both the Imgur URL and local path.
        
        Args:
            image_path: Path to the local image file
            
        Returns:
            Tuple containing (imgur_url, local_path)
            
        Raises:
            ValueError: If image file doesn't exist
            requests.exceptions.RequestException: If upload fails
        """
        if not os.path.exists(image_path):
            raise ValueError(f"Image file not found: {image_path}")
            
        try:
            with open(image_path, 'rb') as image_file:
                files = {'image': image_file}
                response = requests.post(
                    f"{self.base_url}/image",
                    headers=self.headers,
                    files=files
                )
                response.raise_for_status()
                
                data = response.json()
                if not data.get('success'):
                    raise requests.exceptions.RequestException(
                        f"Imgur API error: {data.get('data', {}).get('error', 'Unknown error')}"
                    )
                    
                imgur_url = data['data']['link']
                logger.info(f"Successfully uploaded image to Imgur: {imgur_url}")
                
                return imgur_url, image_path
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload image to Imgur: {str(e)}")
            raise
            
    def save_image_locally(self, image_data: bytes, filename: str) -> str:
        """
        Save an image to the local output directory.
        
        Args:
            image_data: Raw image data
            filename: Name for the saved file
            
        Returns:
            Path to the saved image file
        """
        output_dir = Path('outputs/images')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = output_dir / filename
        with open(file_path, 'wb') as f:
            f.write(image_data)
            
        logger.info(f"Saved image locally: {file_path}")
        return str(file_path) 