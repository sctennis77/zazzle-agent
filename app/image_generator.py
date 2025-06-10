import os
import logging
from typing import Optional, Tuple, Dict, Any, List
import httpx
from openai import OpenAI
from openai.types.images_response import ImagesResponse
from dotenv import load_dotenv
from app.clients.imgur_client import ImgurClient
from datetime import datetime
import base64
from app.models import ProductIdea

load_dotenv()

logger = logging.getLogger(__name__)

# Base prompts for image generation with versioning
IMAGE_GENERATION_BASE_PROMPTS = {
    "dall-e-2": {
        "prompt": "You are a incredibly talented designer and illustrator with a passion for stickers. You are inspired by impressionist painters and the style of their paintings. Your designs must be beautiful and creative. Design an image optimized for a 1.5 inch diameter round image on Zazzle.",
        "version": "1.0.0"
    },
    "dall-e-3": {
        "prompt": "You are a incredibly talented designer and illustrator with a passion for stickers. You are inspired by impressionist painters and the style of their paintings. Your designs must be beautiful and creative. Design an image optimized for a 1.5 inch diameter round image on Zazzle.",
        "version": "1.0.0"
    }
}

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
        
    def get_prompt_info(self) -> Dict[str, str]:
        """
        Get the current prompt information for the model.
        
        Returns:
            Dict containing the prompt and version for the current model.
        """
        return IMAGE_GENERATION_BASE_PROMPTS[self.model]
        
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
            logger.info(f"Generating image for prompt: '{prompt}' with size: {size} with model: {self.model} ")
            
            # Get the base prompt for the model
            base_prompt = IMAGE_GENERATION_BASE_PROMPTS[self.model]["prompt"]
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
                model=self.model,
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

    async def generate_images_batch(self, product_ideas: List[ProductIdea]) -> List[object]:
        """
        Generate images for a batch of product ideas.
        
        Args:
            product_ideas: List of ProductIdea objects
            
        Returns:
            List of ProductInfo objects (or error dicts if generation fails)
            
        Raises:
            ImageGenerationError: If image generation fails for any product idea
        """
        results = []
        for idea in product_ideas:
            try:
                prompt = idea.image_description
                template_id = idea.design_instructions.get('template_id') if idea.design_instructions else None

                if not prompt:
                    logger.warning("Skipping product idea with no image description")
                    continue

                # Generate image (mocked in tests)
                img_result = await self._generate_image(prompt, idea.model)
                imgur_url = img_result['url']
                local_path = img_result['local_path']

                # Create ProductInfo object
                from app.models import ProductInfo  # Local import to avoid circular import
                product_info = ProductInfo(
                    product_id=f"generated_{idea.theme}_{idea.model}",
                    name=f"Generated Product for {idea.theme}",
                    product_type=idea.design_instructions.get('product_type', 'sticker') if idea.design_instructions else 'sticker',
                    image_url=imgur_url,
                    product_url=imgur_url,  # Placeholder, update as needed
                    zazzle_template_id=template_id or '',
                    zazzle_tracking_code='',
                    theme=idea.theme,
                    model=idea.model,
                    prompt_version=idea.prompt_version,
                    reddit_context=idea.reddit_context,
                    design_instructions=idea.design_instructions,
                    image_local_path=local_path
                )
                results.append(product_info)

            except Exception as e:
                logger.error(f"Failed to generate image for product idea: {str(e)}")
                results.append({
                    'error': str(e),
                    'prompt': prompt if 'prompt' in locals() else None,
                    'template_id': template_id if 'template_id' in locals() else None
                })

        return results 