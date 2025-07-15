"""
Reddit agent module for the Zazzle Agent application.

This module defines the RedditAgent, which automates content distribution, product idea generation,
image creation, and engagement on Reddit. It integrates with OpenAI, PRAW, and Zazzle product workflows.
"""

# Remove the base import since we're not inheriting from it anymore
# from .base import ChannelAgent
import asyncio
import json
import logging
import os
import random
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import openai
import praw
from openai import OpenAI
from sqlalchemy.orm import Session

from app.affiliate_linker import ZazzleAffiliateLinker

# Remove legacy distribution imports
# from app.distribution.reddit import RedditDistributionChannel, RedditDistributionError
from app.async_image_generator import IMAGE_GENERATION_BASE_PROMPTS, AsyncImageGenerator
from app.clients.imgur_client import ImgurClient
from app.clients.reddit_client import RedditClient
from app.db.database import SessionLocal
from app.db.mappers import product_idea_to_db, product_info_to_db, reddit_context_to_db
from app.db.models import ProductInfo, RedditPost
from app.models import (
    DesignInstructions,
    DistributionMetadata,
    DistributionStatus,
    PipelineConfig,
    ProductIdea,
    ProductInfo,
    RedditContext,
)
from app.pipeline_status import PipelineStatus
from app.utils.logging_config import get_logger
from app.utils.openai_usage_tracker import log_session_summary, track_openai_call
from app.zazzle_product_designer import ZazzleProductDesigner
from app.zazzle_templates import ZAZZLE_PRINT_TEMPLATE

logger = get_logger(__name__)

# Available subreddits for the agent to work with
AVAILABLE_SUBREDDITS = [
    # Nature & Outdoors (High visual appeal, engaged communities)
    "nature",
    "earthporn",
    "landscapephotography",
    "hiking",
    "camping",
    "gardening",
    "plants",
    "succulents",
    # Space & Science (Fascinating visuals, tech-savvy audience)
    "space",
    "astrophotography",
    "nasa",
    "science",
    "physics",
    "chemistry",
    "biology",
    # Sports & Recreation (Passionate communities, great visuals)
    "golf",
    "soccer",
    "basketball",
    "tennis",
    "baseball",
    "hockey",
    "fishing",
    "surfing",
    "skiing",
    "rockclimbing",
    # Animals & Pets (Universal appeal, emotional connection)
    "aww",
    "cats",
    "dogs",
    "puppies",
    "kittens",
    "wildlife",
    "birding",
    "aquariums",
    # Food & Cooking (Visual appeal, lifestyle audience)
    "food",
    "foodporn",
    "cooking",
    "baking",
    "coffee",
    "tea",
    "wine",
    # Art & Design (Creative communities, design appreciation)
    "art",
    "design",
    "architecture",
    "interiordesign",
    "streetart",
    "digitalart",
    # Technology & Gaming (Tech-savvy, purchasing power)
    "programming",
    "gaming",
    "pcgaming",
    "retrogaming",
    "cyberpunk",
    "futurology",
    # Travel & Culture (Diverse visuals, adventurous audience)
    "travel",
    "backpacking",
    "photography",
    "cityporn",
    "history",
    # Lifestyle & Wellness (Health-conscious, purchasing power)
    "fitness",
    "yoga",
    "meditation",
    "minimalism",
    "sustainability",
    "vegan",
]

# Detailed criteria for each subreddit selection
SUBREDDIT_CRITERIA = {
    # Nature & Outdoors
    "nature": {
        "image_generation": "Excellent - Diverse landscapes, wildlife, natural phenomena provide rich visual content",
        "engagement": "High - Nature enthusiasts are passionate and likely to purchase nature-themed products",
        "purchase_likelihood": "Very High - Nature lovers often buy decor, clothing, and accessories",
    },
    "earthporn": {
        "image_generation": "Outstanding - Stunning landscape photography with dramatic lighting and composition",
        "engagement": "Very High - Photography enthusiasts with appreciation for visual art",
        "purchase_likelihood": "High - Likely to buy prints, wall art, and photography-related products",
    },
    "landscapephotography": {
        "image_generation": "Excellent - Professional quality landscape images with artistic composition",
        "engagement": "High - Photography community with technical knowledge and appreciation",
        "purchase_likelihood": "High - Photography enthusiasts often purchase related products",
    },
    "hiking": {
        "image_generation": "Very Good - Trail views, mountain vistas, outdoor adventure scenes",
        "engagement": "High - Active outdoor community with strong passion for nature",
        "purchase_likelihood": "Very High - Hikers buy gear, clothing, and outdoor-themed products",
    },
    "camping": {
        "image_generation": "Good - Campfire scenes, tent setups, wilderness camping",
        "engagement": "High - Outdoor enthusiasts with strong community bonds",
        "purchase_likelihood": "Very High - Campers regularly buy outdoor gear and accessories",
    },
    "gardening": {
        "image_generation": "Very Good - Beautiful gardens, flowers, plants, garden design",
        "engagement": "High - Gardening community with strong passion and knowledge",
        "purchase_likelihood": "High - Gardeners buy tools, decor, and garden-themed products",
    },
    "plants": {
        "image_generation": "Excellent - Diverse plant species, indoor/outdoor plants, botanical beauty",
        "engagement": "Very High - Plant enthusiasts with strong community and knowledge sharing",
        "purchase_likelihood": "Very High - Plant lovers buy planters, decor, and plant-related items",
    },
    "succulents": {
        "image_generation": "Very Good - Unique succulent varieties, arrangements, minimalist beauty",
        "engagement": "High - Dedicated succulent community with strong passion",
        "purchase_likelihood": "High - Succulent enthusiasts buy planters and related products",
    },
    # Space & Science
    "space": {
        "image_generation": "Outstanding - Nebulae, galaxies, planets, space phenomena with stunning visuals",
        "engagement": "Very High - Space enthusiasts with strong interest and knowledge",
        "purchase_likelihood": "High - Space fans buy posters, clothing, and space-themed products",
    },
    "astrophotography": {
        "image_generation": "Exceptional - Professional space photography with incredible detail and beauty",
        "engagement": "Very High - Photography and space enthusiasts with technical expertise",
        "purchase_likelihood": "High - Likely to purchase prints and space-themed decor",
    },
    "nasa": {
        "image_generation": "Excellent - Official NASA imagery, spacecraft, astronauts, mission photos",
        "engagement": "Very High - Space and science enthusiasts with strong interest",
        "purchase_likelihood": "High - NASA fans buy official merchandise and space-themed products",
    },
    "science": {
        "image_generation": "Good - Scientific concepts, experiments, research visuals",
        "engagement": "High - Science enthusiasts with strong intellectual curiosity",
        "purchase_likelihood": "Medium-High - Science fans buy educational and themed products",
    },
    "physics": {
        "image_generation": "Good - Physics concepts, diagrams, experimental setups",
        "engagement": "High - Physics enthusiasts with strong technical knowledge",
        "purchase_likelihood": "Medium-High - Physics fans buy educational and themed products",
    },
    "chemistry": {
        "image_generation": "Good - Chemical reactions, lab setups, molecular structures",
        "engagement": "High - Chemistry enthusiasts with strong interest in science",
        "purchase_likelihood": "Medium-High - Chemistry fans buy educational and themed products",
    },
    "biology": {
        "image_generation": "Very Good - Microscopic life, ecosystems, biological diversity",
        "engagement": "High - Biology enthusiasts with strong interest in life sciences",
        "purchase_likelihood": "Medium-High - Biology fans buy educational and themed products",
    },
    # Sports & Recreation
    "golf": {
        "image_generation": "Good - Golf courses, equipment, players, scenic golf settings",
        "engagement": "Very High - Golf enthusiasts with strong passion and purchasing power",
        "purchase_likelihood": "Very High - Golfers buy equipment, clothing, and golf-themed products",
    },
    "soccer": {
        "image_generation": "Good - Stadiums, players, action shots, team colors",
        "engagement": "Very High - Global soccer community with massive following",
        "purchase_likelihood": "Very High - Soccer fans buy jerseys, memorabilia, and team products",
    },
    "basketball": {
        "image_generation": "Good - Courts, players, action shots, team colors",
        "engagement": "Very High - Basketball community with strong passion",
        "purchase_likelihood": "Very High - Basketball fans buy jerseys, memorabilia, and team products",
    },
    "tennis": {
        "image_generation": "Good - Courts, players, equipment, tennis settings",
        "engagement": "High - Tennis enthusiasts with strong community",
        "purchase_likelihood": "High - Tennis players buy equipment, clothing, and tennis products",
    },
    "baseball": {
        "image_generation": "Good - Stadiums, players, fields, team colors",
        "engagement": "Very High - Baseball community with strong tradition and passion",
        "purchase_likelihood": "Very High - Baseball fans buy memorabilia, jerseys, and team products",
    },
    "hockey": {
        "image_generation": "Good - Rinks, players, equipment, team colors",
        "engagement": "High - Hockey community with strong passion",
        "purchase_likelihood": "High - Hockey fans buy jerseys, memorabilia, and team products",
    },
    "fishing": {
        "image_generation": "Very Good - Fishing scenes, water, boats, fish, outdoor settings",
        "engagement": "High - Fishing enthusiasts with strong community",
        "purchase_likelihood": "Very High - Fishermen buy equipment, clothing, and fishing products",
    },
    "surfing": {
        "image_generation": "Excellent - Ocean waves, surfers, beach scenes, coastal beauty",
        "engagement": "High - Surfing community with strong passion for ocean",
        "purchase_likelihood": "High - Surfers buy equipment, clothing, and ocean-themed products",
    },
    "skiing": {
        "image_generation": "Excellent - Snow-covered mountains, skiers, winter sports",
        "engagement": "High - Skiing community with strong passion for winter sports",
        "purchase_likelihood": "High - Skiers buy equipment, clothing, and winter-themed products",
    },
    "rockclimbing": {
        "image_generation": "Very Good - Cliffs, climbers, outdoor adventure, scenic views",
        "engagement": "High - Climbing community with strong passion for adventure",
        "purchase_likelihood": "High - Climbers buy equipment, clothing, and adventure products",
    },
    # Animals & Pets
    "aww": {
        "image_generation": "Excellent - Cute animals, pets, heartwarming moments",
        "engagement": "Very High - Universal appeal, massive community",
        "purchase_likelihood": "Very High - Pet owners buy pet-related products and cute animal items",
    },
    "cats": {
        "image_generation": "Excellent - Cat photos, behaviors, cute moments",
        "engagement": "Very High - Cat lovers with strong community and passion",
        "purchase_likelihood": "Very High - Cat owners buy cat-themed products and accessories",
    },
    "dogs": {
        "image_generation": "Excellent - Dog photos, behaviors, cute moments",
        "engagement": "Very High - Dog lovers with strong community and passion",
        "purchase_likelihood": "Very High - Dog owners buy dog-themed products and accessories",
    },
    "puppies": {
        "image_generation": "Excellent - Puppy photos, cute moments, playful scenes",
        "engagement": "Very High - Universal appeal, emotional connection",
        "purchase_likelihood": "Very High - Puppy owners buy pet products and cute items",
    },
    "kittens": {
        "image_generation": "Excellent - Kitten photos, cute moments, playful scenes",
        "engagement": "Very High - Universal appeal, emotional connection",
        "purchase_likelihood": "Very High - Kitten owners buy pet products and cute items",
    },
    "wildlife": {
        "image_generation": "Excellent - Wild animals, natural behaviors, diverse species",
        "engagement": "High - Wildlife enthusiasts with strong interest in nature",
        "purchase_likelihood": "High - Wildlife fans buy nature-themed products and decor",
    },
    "birding": {
        "image_generation": "Very Good - Bird species, natural habitats, bird behaviors",
        "engagement": "High - Birding community with strong passion and knowledge",
        "purchase_likelihood": "High - Birders buy equipment, guides, and bird-themed products",
    },
    "aquariums": {
        "image_generation": "Very Good - Fish, aquatic plants, tank setups, underwater scenes",
        "engagement": "High - Aquarium enthusiasts with strong community",
        "purchase_likelihood": "High - Aquarium owners buy equipment, decor, and fish products",
    },
    # Food & Cooking
    "food": {
        "image_generation": "Excellent - Diverse cuisines, cooking, presentation, food photography",
        "engagement": "Very High - Food lovers with strong community and passion",
        "purchase_likelihood": "High - Food enthusiasts buy kitchen products and food-themed items",
    },
    "foodporn": {
        "image_generation": "Outstanding - High-quality food photography, presentation, culinary art",
        "engagement": "Very High - Food photography enthusiasts with appreciation for visual appeal",
        "purchase_likelihood": "High - Likely to buy kitchen products and food-themed decor",
    },
    "cooking": {
        "image_generation": "Good - Cooking processes, ingredients, kitchen scenes",
        "engagement": "Very High - Cooking enthusiasts with strong community",
        "purchase_likelihood": "Very High - Cooks buy kitchen equipment and cooking products",
    },
    "baking": {
        "image_generation": "Very Good - Baked goods, pastries, desserts, baking process",
        "engagement": "High - Baking enthusiasts with strong passion",
        "purchase_likelihood": "High - Bakers buy baking equipment and kitchen products",
    },
    "coffee": {
        "image_generation": "Very Good - Coffee drinks, cafes, brewing, coffee culture",
        "engagement": "High - Coffee enthusiasts with strong community",
        "purchase_likelihood": "High - Coffee lovers buy brewing equipment and coffee products",
    },
    "tea": {
        "image_generation": "Good - Tea varieties, brewing, tea culture, relaxation",
        "engagement": "High - Tea enthusiasts with strong community",
        "purchase_likelihood": "High - Tea lovers buy brewing equipment and tea products",
    },
    "wine": {
        "image_generation": "Good - Wine bottles, vineyards, wine culture, tasting",
        "engagement": "High - Wine enthusiasts with strong community and purchasing power",
        "purchase_likelihood": "High - Wine lovers buy wine accessories and wine-themed products",
    },
    # Art & Design
    "art": {
        "image_generation": "Excellent - Diverse art styles, creativity, artistic expression",
        "engagement": "Very High - Art enthusiasts with strong appreciation for creativity",
        "purchase_likelihood": "High - Art lovers buy art supplies and artistic products",
    },
    "design": {
        "image_generation": "Very Good - Design concepts, layouts, visual design",
        "engagement": "High - Design professionals and enthusiasts",
        "purchase_likelihood": "High - Designers buy design tools and design-themed products",
    },
    "architecture": {
        "image_generation": "Excellent - Buildings, structures, architectural beauty",
        "engagement": "High - Architecture enthusiasts with strong appreciation",
        "purchase_likelihood": "Medium-High - Architecture fans buy architectural products and decor",
    },
    "interiordesign": {
        "image_generation": "Very Good - Room designs, furniture, decor, home aesthetics",
        "engagement": "High - Interior design enthusiasts with strong interest",
        "purchase_likelihood": "High - Design enthusiasts buy home decor and design products",
    },
    "streetart": {
        "image_generation": "Excellent - Urban art, murals, graffiti, street culture",
        "engagement": "High - Street art enthusiasts with strong appreciation",
        "purchase_likelihood": "Medium-High - Street art fans buy urban-themed products",
    },
    "digitalart": {
        "image_generation": "Very Good - Digital artwork, digital painting, digital design",
        "engagement": "High - Digital artists and enthusiasts",
        "purchase_likelihood": "High - Digital artists buy digital tools and art products",
    },
    # Technology & Gaming
    "programming": {
        "image_generation": "Good - Code, technology concepts, programming themes",
        "engagement": "Very High - Programmers with strong community and purchasing power",
        "purchase_likelihood": "High - Programmers buy tech products and programming-themed items",
    },
    "gaming": {
        "image_generation": "Good - Game characters, scenes, gaming culture",
        "engagement": "Very High - Gaming community with massive following",
        "purchase_likelihood": "Very High - Gamers buy gaming products and merchandise",
    },
    "pcgaming": {
        "image_generation": "Good - PC setups, gaming hardware, gaming culture",
        "engagement": "Very High - PC gaming community with strong purchasing power",
        "purchase_likelihood": "Very High - PC gamers buy hardware and gaming products",
    },
    "retrogaming": {
        "image_generation": "Good - Retro games, classic consoles, nostalgic gaming",
        "engagement": "High - Retro gaming enthusiasts with strong nostalgia",
        "purchase_likelihood": "High - Retro gamers buy vintage and retro-themed products",
    },
    "cyberpunk": {
        "image_generation": "Excellent - Futuristic aesthetics, neon, cyberpunk themes",
        "engagement": "High - Cyberpunk enthusiasts with strong aesthetic appreciation",
        "purchase_likelihood": "High - Cyberpunk fans buy themed products and decor",
    },
    "futurology": {
        "image_generation": "Good - Future concepts, technology, innovation themes",
        "engagement": "High - Future enthusiasts with strong interest in technology",
        "purchase_likelihood": "Medium-High - Future enthusiasts buy tech and innovation products",
    },
    # Travel & Culture
    "travel": {
        "image_generation": "Excellent - Travel destinations, cultures, landscapes, experiences",
        "engagement": "Very High - Travel enthusiasts with strong passion for exploration",
        "purchase_likelihood": "High - Travelers buy travel products and destination-themed items",
    },
    "backpacking": {
        "image_generation": "Very Good - Backpacking scenes, trails, outdoor adventure",
        "engagement": "High - Backpacking community with strong passion for adventure",
        "purchase_likelihood": "High - Backpackers buy outdoor gear and travel products",
    },
    "photography": {
        "image_generation": "Excellent - Diverse photography styles, techniques, subjects",
        "engagement": "Very High - Photography enthusiasts with strong technical knowledge",
        "purchase_likelihood": "High - Photographers buy equipment and photography products",
    },
    "cityporn": {
        "image_generation": "Excellent - Urban landscapes, cityscapes, architecture",
        "engagement": "High - Urban photography enthusiasts with appreciation for cities",
        "purchase_likelihood": "Medium-High - City enthusiasts buy urban-themed products",
    },
    "history": {
        "image_generation": "Good - Historical artifacts, events, historical themes",
        "engagement": "High - History enthusiasts with strong interest in the past",
        "purchase_likelihood": "Medium-High - History fans buy historical and educational products",
    },
    # Lifestyle & Wellness
    "fitness": {
        "image_generation": "Good - Exercise, fitness, health, active lifestyle",
        "engagement": "Very High - Fitness enthusiasts with strong community",
        "purchase_likelihood": "Very High - Fitness enthusiasts buy equipment and fitness products",
    },
    "yoga": {
        "image_generation": "Very Good - Yoga poses, meditation, wellness, tranquility",
        "engagement": "High - Yoga community with strong passion for wellness",
        "purchase_likelihood": "High - Yogis buy yoga equipment and wellness products",
    },
    "meditation": {
        "image_generation": "Good - Meditation, mindfulness, peace, tranquility",
        "engagement": "High - Meditation community with strong interest in wellness",
        "purchase_likelihood": "High - Meditators buy wellness products and meditation items",
    },
    "minimalism": {
        "image_generation": "Good - Clean design, simplicity, minimalist aesthetics",
        "engagement": "High - Minimalist community with appreciation for simplicity",
        "purchase_likelihood": "High - Minimalists buy quality, simple products",
    },
    "sustainability": {
        "image_generation": "Good - Eco-friendly concepts, nature, sustainable living",
        "engagement": "High - Sustainability enthusiasts with strong environmental values",
        "purchase_likelihood": "High - Sustainability advocates buy eco-friendly products",
    },
    "vegan": {
        "image_generation": "Good - Plant-based food, vegan lifestyle, animal welfare",
        "engagement": "High - Vegan community with strong values and passion",
        "purchase_likelihood": "High - Vegans buy plant-based and ethical products",
    },
}


def pick_subreddit(db: Session = None) -> str:
    """
    Pick a random subreddit, trying to fetch a new one from Reddit first,
    then falling back to database or hardcoded list.

    Args:
        db: Database session. If None, creates a new session.

    Returns:
        str: A randomly selected subreddit name

    Raises:
        Exception: If no subreddits are available in the database
    """
    if db is None:
        from app.db.database import SessionLocal

        db = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        from app.clients.reddit_client import RedditClient
        from app.db.models import Subreddit
        import logging

        logger = logging.getLogger(__name__)

        # Try to fetch a random subreddit from Reddit's API
        reddit_client = RedditClient()
        random_subreddit_name = reddit_client.fetch_random_subreddit()

        if random_subreddit_name:
            # Check if this subreddit already exists in our database
            existing_subreddit = db.query(Subreddit).filter_by(
                subreddit_name=random_subreddit_name
            ).first()

            if not existing_subreddit:
                # Try to get subreddit info and add it to database
                try:
                    subreddit_info = reddit_client.get_subreddit_info(
                        random_subreddit_name
                    )
                    
                    # Create new subreddit entry
                    new_subreddit = Subreddit(
                        subreddit_name=random_subreddit_name,
                        display_name=subreddit_info.get("display_name"),
                        description=subreddit_info.get("description"),
                        public_description=subreddit_info.get("public_description"),
                        subscribers=subreddit_info.get("subscribers"),
                        over18=subreddit_info.get("over18", False)
                    )
                    
                    db.add(new_subreddit)
                    db.commit()
                    
                    logger.info(
                        f"Added new subreddit to database: {random_subreddit_name}"
                    )
                    
                except Exception as e:
                    logger.warning(
                        f"Failed to get info for subreddit {random_subreddit_name}: {e}"
                    )
                    db.rollback()

            return random_subreddit_name

        # Fallback to existing database subreddits
        subreddits = db.query(Subreddit).all()

        if subreddits:
            selected_subreddit = random.choice(subreddits)
            return selected_subreddit.subreddit_name

        # Final fallback to hardcoded list if database is empty
        logger.warning(
            "No subreddits found in database and failed to fetch from Reddit, "
            "falling back to hardcoded list"
        )
        return random.choice(AVAILABLE_SUBREDDITS)

    finally:
        if should_close:
            db.close()


class RedditAgent:
    """
    Reddit agent for product idea generation and creation.

    This agent focuses on finding trending posts, generating product ideas,
    creating images, and designing products on Zazzle. Interaction logic
    has been moved to RedditInteractionAgent.
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        pipeline_run_id: int = None,
        session: Session = None,
        reddit_post_id: int = None,
        subreddit_name: str = "golf",
        reddit_client: Optional[Any] = None,
        task_context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None,
    ):
        """
        Initialize the Reddit agent.

        Args:
            config: Pipeline configuration
            pipeline_run_id: ID of the current pipeline run
            session: SQLAlchemy session for DB operations
            reddit_post_id: ID of the current Reddit post
            subreddit_name: Target subreddit name
            reddit_client: Optional Reddit client for testing
            task_context: Optional task context data for commissioning
        """
        self.config = config or PipelineConfig(
            model="dall-e-3",
            zazzle_template_id=ZAZZLE_PRINT_TEMPLATE.zazzle_template_id,
            zazzle_tracking_code=ZAZZLE_PRINT_TEMPLATE.zazzle_tracking_code,
            zazzle_affiliate_id=os.getenv("ZAZZLE_AFFILIATE_ID", ""),
            prompt_version="1.0.0",
        )
        self.pipeline_run_id = pipeline_run_id
        self.session = session
        self.reddit_post_id = reddit_post_id
        self.subreddit_name = subreddit_name
        self.commission_message = (
            None  # Optional commission message for commissioned posts
        )
        self.task_context = task_context or {}  # Task context for commissioning logic
        self.progress_callback = progress_callback  # Callback for progress updates

        # Initialize Reddit client
        if reddit_client:
            self.reddit_client = reddit_client
        else:
            self.reddit_client = RedditClient()

        # Initialize other components
        self.imgur_client = ImgurClient()
        self.image_generator = AsyncImageGenerator(
            model=self.config.model, quality=self.config.image_quality
        )
        self.zazzle_designer = ZazzleProductDesigner()
        self.affiliate_linker = ZazzleAffiliateLinker(
            zazzle_affiliate_id=self.config.zazzle_affiliate_id,
            zazzle_tracking_code=self.config.zazzle_tracking_code,
        )

        # Set OpenAI API key and initialize client
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.openai = OpenAI(api_key=openai.api_key)  # Initialize the OpenAI client

        # Set the idea generation model
        self.idea_model = self._get_idea_model()

        logger.info(f"Initialized RedditAgent for subreddit: {self.subreddit_name}")
        logger.info(f"Using idea model: {self.idea_model}")
        logger.info(f"Using image model: {self.config.model}")
        logger.info(f"Pipeline run ID: {self.pipeline_run_id}")
        logger.info(f"Reddit post ID: {self.reddit_post_id}")
        if self.task_context:
            logger.info(f"Task context: {self.task_context}")

        # Initialize usage tracking
        log_session_summary()

    def _get_idea_model(self) -> str:
        """
        Get the model to use for product idea generation.
        Uses the OPENAI_IDEA_MODEL environment variable, defaults to gpt-4o-mini.
        """
        return os.getenv("OPENAI_IDEA_MODEL", "gpt-4o-mini")

    async def _send_image_generation_progress(
        self, delay: int = 1, image_title: str = None
    ):
        """Send key progress milestones during image generation."""
        try:
            logger.debug("Starting image generation progress updates")
            await asyncio.sleep(delay)

            # Only log key milestones: start, 25%, 50%, 75%, 90%
            milestones = [40, 55, 70, 85, 89]

            for i, progress in enumerate(milestones):
                if self.progress_callback:
                    try:
                        await self.progress_callback(
                            "image_generation_progress", {"progress": progress}
                        )
                        if progress in [40, 89]:  # Only log start and end
                            logger.info(f"Image generation progress: {progress}%")
                    except Exception as e:
                        logger.error(f"Progress callback failed at {progress}%: {e}")

                if i < len(milestones) - 1:
                    await asyncio.sleep(random.uniform(2.0, 3.0))  # Longer intervals

            # Simplified event coordination
            if hasattr(self, "image_generation_event") and self.image_generation_event:
                await self.image_generation_event.wait()
                logger.debug("Image generation completed")

        except asyncio.CancelledError:
            logger.debug("Progress updates cancelled")
            raise
        except Exception as e:
            logger.error(f"Progress update error: {e}")

    def _make_openai_call(self, messages: List[Dict[str, str]]) -> str:
        """
        Make an OpenAI API call with tracking.
        Uses the model specified by _get_idea_model().
        """
        model = self._get_idea_model()
        
        # Apply tracking with the actual model being used
        @track_openai_call(model=model, operation="chat")
        def _tracked_call():
            response = self.openai.chat.completions.create(model=model, messages=messages)
            return response.choices[0].message.content
            
        return _tracked_call()

    async def _determine_product_idea(
        self, reddit_context: RedditContext
    ) -> Optional[ProductIdea]:
        """
        Determine product idea from Reddit post context using OpenAI.

        Args:
            reddit_context: RedditContext object with post details

        Returns:
            ProductIdea object or None if generation fails

        Raises:
            ValueError: If theme is 'default theme' or image description is empty
        """
        try:
            # Use OpenAI to analyze post and generate product idea
            # TODO: need to version these too
            log_cnt = f"Reddit Post:\nTitle: {reddit_context.post_title}\nContent: {reddit_context.post_content if reddit_context.post_content else 'No content'}\nComment Summary: {reddit_context.comments[0]['text'] if reddit_context.comments and reddit_context.comments[0].get('text') else 'No comments'}\n\nExtract the core story and create:\nTheme: [The essence or key moment]\nImage Title: [A concise, witty and insightful title reflecting the theme and comment summary]\nImage Description: [A vivid, specific visual scene for DALL-E-3]"
            logger.info(f"Generating product idea for Reddit post: {log_cnt}")
            messages = [
                {
                    "role": "system",
                    "content": "You are a creative storyteller who creates visual narratives from Reddit posts. Extract and set the beautiful scene for a captivating story(emotion, conflict, symbolism, abstract concepts, dreams, etc. are all good. Be really creative and imaginative.) from the post title, post content (if available) and especially leverage the comment summary. Next take this idea and revise it into an image description that will be passed to a reddit illustrator using DALL-E-3 to generate images.  The illustrator loves drawing nature and beautiful animals (when relevant). Keep image descriptions concise ( < 7 sentences). The illustrator does not render text well. Also create a concise, witty and insightful title (one sentence max) that captures the essence of the theme and comment summary.",
                },
                {
                    "role": "user",
                    "content": f"Reddit Post:\nTitle: {reddit_context.post_title}\nContent: {reddit_context.post_content if reddit_context.post_content else 'No content'}\nComment Summary: {reddit_context.comments[0]['text'] if reddit_context.comments and reddit_context.comments[0].get('text') else 'No comments'}\n\nExtract the core story and create:\nTheme: [The essence or key moment]\nImage Title: [A concise, witty and insightful title reflecting the theme and comment summary]\nImage Description: [A vivid, specific visual scene for DALL-E-3]",
                },
            ]

            content = self._make_openai_call(messages)

            # Log the raw response for debugging
            logger.info(f"Raw OpenAI Response: {content}")

            # Parse response to get theme, image title, and image description
            lines = content.split("\n")
            logger.info(f"OpenAI Response: {lines}")
            theme = None
            image_title = None
            image_description = None
            for line in lines:
                if line.startswith("Theme:"):
                    theme = line.replace("Theme:", "").strip().strip('"')
                elif line.startswith("Image Title:"):
                    image_title = line.replace("Image Title:", "").strip().strip('"')
                elif line.startswith("Image Description:"):
                    image_description = line.replace("Image Description:", "").strip()

            # Treat empty strings as missing
            if not theme or not theme.strip():
                error_msg = "No theme found in OpenAI response"
                logger.error(error_msg)
                return None
            if not image_description or not image_description.strip():
                error_msg = "No image description found in OpenAI response"
                logger.error(error_msg)
                raise ValueError(error_msg)

            if theme.lower() == "default theme":
                error_msg = "Invalid theme: 'default theme' is not allowed"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Create product idea
            product_idea = ProductIdea(
                theme=theme,
                image_description=image_description,
                design_instructions={
                    "image": None,
                    "theme": theme,
                    "image_title": image_title,
                },
                reddit_context=reddit_context,
                model=self.config.model,
                prompt_version=self.config.prompt_version,
            )

            logger.info(f"Successfully generated product idea: {theme}")
            if image_title:
                logger.info(f"Generated image title: {image_title}")

            # Call progress callback if available
            if self.progress_callback:
                try:
                    await self.progress_callback(
                        "product_designed",
                        {
                            "theme": theme,
                            "image_title": image_title,
                            "image_description": image_description,
                        },
                    )
                except Exception as e:
                    logger.error(f"Error calling progress callback: {e}")

            return product_idea

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error determining product idea: {str(e)}")
            return None

    async def find_and_create_product_for_task(self) -> Optional[ProductInfo]:
        """
        Find a trending post and create a product for it.
        This is the main entry point for task-based product creation.
        """
        logger.debug("Starting task-based product creation")
        logger.debug(f"Task context: {self.task_context}")

        try:
            # Find a trending post using task-specific method
            trending_post = await self._find_trending_post_for_task()
            if not trending_post:
                logger.warning("No suitable trending post found for task")
                return None

            # Log trending post details
            logger.info("Found trending post for task:")
            logger.info(f"Post ID: {trending_post.id}")
            logger.info(f"Title: {trending_post.title}")
            logger.info(f"URL: {trending_post.url}")
            logger.info(f"Subreddit: {trending_post.subreddit.display_name}")
            logger.info(
                f"Content: {trending_post.selftext if hasattr(trending_post, 'selftext') else 'No content'}"
            )
            logger.info(
                f"Comment Summary: {getattr(trending_post, 'comment_summary', 'No comment summary')}"
            )

            # Create RedditContext from the post
            reddit_context = RedditContext(
                post_id=trending_post.id,
                post_title=trending_post.title,
                post_url=f"https://reddit.com{trending_post.permalink}",
                subreddit=trending_post.subreddit.display_name,
                post_content=(
                    trending_post.selftext
                    if hasattr(trending_post, "selftext")
                    else None
                ),
                permalink=trending_post.permalink,
                author=str(trending_post.author) if trending_post.author else None,
                score=trending_post.score,
                num_comments=trending_post.num_comments,
                comments=[
                    {
                        "text": getattr(
                            trending_post, "comment_summary", "No comment summary"
                        )
                    }
                ],
            )

            # Determine product idea from post (asynchronous call)
            product_idea = await self._determine_product_idea(reddit_context)
            if not product_idea:
                logger.warning("Could not determine product idea from post")
                return None
            if not product_idea.theme or product_idea.theme.lower() == "default theme":
                raise ValueError("No valid theme was generated from the Reddit context")
            logger.info(f"Product Idea: {product_idea}")
            if (
                not product_idea.image_description
                or not product_idea.image_description.strip()
            ):
                logger.error(
                    "Image prompt (image_description) is empty. Aborting image generation."
                )
                raise ValueError("Image prompt (image_description) cannot be empty.")

            logger.info("=== ABOUT TO START IMAGE GENERATION ===")
            logger.info(
                f"Progress callback at image generation: {self.progress_callback}"
            )

            # Initialize progress_task to avoid UnboundLocalError
            progress_task = None
            
            # Call image generation started callback
            if self.progress_callback:
                try:
                    logger.info("Calling image generation started callback")
                    logger.info(f"Progress callback function: {self.progress_callback}")
                    await self.progress_callback(
                        "image_generation_started",
                        {
                            "post_id": reddit_context.post_id,
                            "subreddit_name": reddit_context.subreddit,
                        },
                    )
                    logger.info("Successfully called image generation started callback")
                except Exception as e:
                    logger.error(
                        f"Error calling image generation started callback: {e}"
                    )
                    logger.error(f"Exception type: {type(e)}")
                    import traceback

                    logger.error(f"Traceback: {traceback.format_exc()}")

                # Start progress updates as a background task
                if self.progress_callback:
                    try:
                        # Create event for coordinating progress task with image generation
                        self.image_generation_event = asyncio.Event()
                        progress_task = asyncio.create_task(
                            self._send_image_generation_progress()
                        )
                        logger.debug("Progress task created for image generation")
                    except Exception as e:
                        logger.error(f"Error creating progress task: {e}")
                        progress_task = None
                        self.image_generation_event = None
                else:
                    progress_task = None
                    self.image_generation_event = None
                    logger.debug(
                        "No progress callback available, skipping progress task"
                    )

            try:
                # Log the start time
                start_time = time.time()
                logger.info(f"Starting image generation at {start_time}")

                imgur_url, local_path = await self.image_generator.generate_image(
                    product_idea.image_description,
                    template_id=self.config.zazzle_template_id,
                )

                # Log the end time and duration
                end_time = time.time()
                duration = end_time - start_time
                logger.info(
                    f"Image generation completed at {end_time}, duration: {duration:.2f} seconds"
                )

                # Signal that image generation is complete
                if (
                    hasattr(self, "image_generation_event")
                    and self.image_generation_event
                ):
                    self.image_generation_event.set()
                    logger.debug("Image generation event signaled")

            except Exception as e:
                logger.error(f"Error during image generation: {str(e)}")
                # Signal completion even on error so progress task doesn't hang
                if (
                    hasattr(self, "image_generation_event")
                    and self.image_generation_event
                ):
                    self.image_generation_event.set()
                    logger.debug("Image generation event signaled on error")
                raise
            finally:
                # Cancel progress task if it exists
                if progress_task and not progress_task.done():
                    logger.info(f"Cancelling progress task: {progress_task}")
                    progress_task.cancel()
                    try:
                        await progress_task
                    except asyncio.CancelledError:
                        logger.info("Progress task cancelled successfully")
                    except Exception as e:
                        logger.error(f"Error cancelling progress task: {e}")

                # Clean up the event
                if (
                    hasattr(self, "image_generation_event")
                    and self.image_generation_event
                ):
                    self.image_generation_event = None
                    logger.debug("Image generation event cleaned up")

            # Call image generation complete callback
            if self.progress_callback:
                try:
                    await self.progress_callback(
                        "image_generation_complete",
                        {
                            "post_id": reddit_context.post_id,
                            "subreddit_name": reddit_context.subreddit,
                            "duration": duration,
                        },
                    )
                except Exception as e:
                    logger.error(
                        f"Error calling image generation complete callback: {e}"
                    )

            design_instructions = DesignInstructions(
                image=imgur_url,
                theme=product_idea.theme,
                image_title=product_idea.design_instructions.get("image_title"),
                text=product_idea.image_description,
                product_type=ZAZZLE_PRINT_TEMPLATE.product_type,
                template_id=self.config.zazzle_template_id,
                model=self.config.model,
                prompt_version=self.config.prompt_version,
                image_quality=self.config.image_quality,
            )
            logger.info(f"Design Instructions: {design_instructions}")
            product_info = await self.zazzle_designer.create_product(
                design_instructions=design_instructions, reddit_context=reddit_context
            )
            if not product_info:
                logger.warning("Failed to create product")
                return None
            if isinstance(product_info, dict):
                product_info = ProductInfo.from_dict(product_info)
            return product_info
        except Exception as e:
            logger.error(f"Error in find_and_create_product_for_task: {str(e)}")
            return None

    def save_reddit_context_to_db(self, reddit_context) -> Optional[int]:
        """
        Persist a RedditContext as RedditPost in the DB and return the DB ID.

        Returns:
            int: The ID of the persisted RedditPost if successful
            None: If persistence fails or no session/pipeline_run_id is provided
        """
        reddit_post_id = None
        if self.session and self.pipeline_run_id:
            try:
                orm_post = reddit_context_to_db(
                    reddit_context, self.pipeline_run_id, self.session
                )
                self.session.add(orm_post)
                self.session.commit()
                reddit_post_id = orm_post.id
                logger.info(f"Persisted RedditPost with id {reddit_post_id}")
            except Exception as e:
                logger.error(f"Failed to persist RedditPost: {str(e)}")
                self.session.rollback()
                return None
        else:
            logger.warning(
                "No session or pipeline_run_id available for saving RedditPost"
            )
        return reddit_post_id

    async def _find_trending_post_for_task(
        self, tries: int = 3, limit: int = 50, subreddit_name: str = None
    ):
        """
        Find a trending Reddit post specifically for task-based processing.
        This is a simplified version that can be easily tested and mocked.
        Works for both specific subreddits and "all" (front page).
        Skips posts that are stickied, too old, or already present in the database (by post_id).
        Returns the first valid post or None if none are found.
        """
        logger.info(
            f"Starting _find_trending_post_for_task with subreddit: {subreddit_name or self.subreddit_name}, limit: {limit}, retries: {tries}"
        )

        # Check if we have a specific post to commission from task context
        if hasattr(self, "task_context") and self.task_context:
            post_id = self.task_context.get("post_id")
            if post_id:
                logger.info(f"Commissioning specific post: {post_id}")
                try:
                    # Fetch the specific post
                    submission = self.reddit_client.get_post(post_id)
                    if submission:
                        # Generate comment summary and add to submission
                        comment_summary = self._generate_comment_summary(submission)
                        submission.comment_summary = comment_summary
                        logger.info(
                            f"Successfully fetched commissioned post: {submission.title}"
                        )

                        # Call progress callback if available
                        if self.progress_callback:
                            try:
                                await self.progress_callback(
                                    "post_fetched",
                                    {
                                        "post_title": submission.title,
                                        "post_id": submission.id,
                                        "subreddit": submission.subreddit.display_name,
                                    },
                                )
                            except Exception as e:
                                logger.error(f"Error calling progress callback: {e}")

                        return submission
                    else:
                        logger.error(f"Failed to fetch commissioned post {post_id}")
                        return None
                except Exception as e:
                    logger.error(
                        f"Error fetching commissioned post {post_id}: {str(e)}"
                    )
                    return None

        # Otherwise, find a random trending post
        try:
            for attempt in range(tries):
                # Use the existing subreddit object (works for "all" and specific subreddits)
                for submission in self.reddit_client.reddit.subreddit(
                    subreddit_name or self.subreddit_name
                ).hot(limit=limit):
                    logger.info(
                        f"Processing submission: {submission.title} (score: {submission.score}, subreddit: {submission.subreddit.display_name}, is_self: {submission.is_self}, selftext length: {len(submission.selftext) if submission.selftext else 0}, age: {(datetime.now(timezone.utc) - datetime.fromtimestamp(submission.created_utc, timezone.utc)).days} days)"
                    )
                    if submission.stickied:
                        continue
                    if (
                        datetime.now(timezone.utc)
                        - datetime.fromtimestamp(submission.created_utc, timezone.utc)
                    ).days > 30:
                        continue
                    if not submission.selftext:
                        continue

                    # Check if already processed
                    if self.session:
                        existing_post = (
                            self.session.query(RedditPost)
                            .filter_by(post_id=submission.id)
                            .first()
                        )
                        if existing_post:
                            logger.info(
                                f"Skipping post {submission.id}: already processed"
                            )
                            continue

                    # Generate comment summary and add to submission
                    comment_summary = self._generate_comment_summary(submission)
                    submission.comment_summary = comment_summary
                    return submission
                # If we reach here, no suitable post was found in this attempt
                logger.info(
                    f"No suitable trending post found on attempt {attempt + 1}/{tries}"
                )
            return None
        except Exception as e:
            logger.error(f"Error finding trending post: {str(e)}")
            return None

    def _generate_comment_summary(self, submission) -> str:
        """
        Generate a summary of the top comments for a Reddit submission.

        Args:
            submission: PRAW submission object

        Returns:
            str: Comment summary
        """
        try:
            # Get top comments and generate summary
            submission.comments.replace_more(limit=0)  # Load top-level comments only
            top_comments = submission.comments.list()[:10]  # Get top 10 comments
            comment_texts = [
                comment.body for comment in top_comments if hasattr(comment, "body")
            ]
            if comment_texts:
                # Use GPT to summarize comments
                response = self.openai.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "Summarize the key points from these Reddit comments in 1-2 sentences.",
                        },
                        {
                            "role": "user",
                            "content": f"Comments:\n{chr(10).join(comment_texts)}",
                        },
                    ],
                )
                comment_summary = response.choices[0].message.content.strip()
            else:
                comment_summary = "No comments available."

            return comment_summary

        except Exception as e:
            logger.error(f"Error generating comment summary: {str(e)}")
            return "Error generating comment summary."

    async def find_top_post_from_subreddit(
        self,
        tries: int = 3,
        limit: int = 100,
        subreddit_name: str = None,
        time_filter: str = "month",
    ):
        """
        Find a top Reddit post from a subreddit using Reddit's top method.
        This method uses the top() method instead of hot() to find the highest-scoring posts.
        Works for both specific subreddits and "all" (front page).
        Skips posts that are stickied, too old, or already present in the database (by post_id).
        Returns the first valid post or None if none are found.

        Args:
            tries: Number of attempts to find a suitable post
            limit: Number of posts to fetch per attempt
            subreddit_name: Name of subreddit to search (defaults to self.subreddit_name)
            time_filter: Time filter for top posts - can be "all", "day", "hour", "month", "week", or "year" (default: "week")
        """
        logger.info(
            f"Starting find_top_post_from_subreddit with subreddit: {subreddit_name or self.subreddit_name}, limit: {limit}, retries: {tries}, time_filter: {time_filter}"
        )

        # Check if we have a specific post to commission from task context
        if hasattr(self, "task_context") and self.task_context:
            post_id = self.task_context.get("post_id")
            if post_id:
                logger.info(f"Commissioning specific post: {post_id}")
                try:
                    # Fetch the specific post
                    submission = self.reddit_client.get_post(post_id)
                    if submission:
                        # Generate comment summary and add to submission
                        comment_summary = self._generate_comment_summary(submission)
                        submission.comment_summary = comment_summary
                        logger.info(
                            f"Successfully fetched commissioned post: {submission.title}"
                        )

                        # Call progress callback if available
                        if self.progress_callback:
                            try:
                                await self.progress_callback(
                                    "post_fetched",
                                    {
                                        "post_title": submission.title,
                                        "post_id": submission.id,
                                        "subreddit": submission.subreddit.display_name,
                                    },
                                )
                            except Exception as e:
                                logger.error(f"Error calling progress callback: {e}")

                        return submission
                    else:
                        logger.error(f"Failed to fetch commissioned post {post_id}")
                        return None
                except Exception as e:
                    logger.error(
                        f"Error fetching commissioned post {post_id}: {str(e)}"
                    )
                    return None

        # Otherwise, find a top post using the top method
        try:
            for attempt in range(tries):
                logger.info(
                    f"Starting attempt {attempt + 1}/{tries} with limit {limit}"
                )
                processed_count = 0
                skipped_stickied = 0
                skipped_old = 0
                skipped_no_selftext = 0
                skipped_already_processed = 0
                # TODO add smarter time filter fallback logic, we should really just curate posts outside of the commision loops and serve them from the db
                # Use the existing subreddit object (works for "all" and specific subreddits)
                for submission in self.reddit_client.reddit.subreddit(
                    subreddit_name or self.subreddit_name
                ).top(time_filter=time_filter, limit=limit):
                    processed_count += 1
                    logger.info(
                        f"Processing submission {processed_count}: {submission.title} (score: {submission.score}, subreddit: {submission.subreddit.display_name}, is_self: {submission.is_self}, selftext length: {len(submission.selftext) if submission.selftext else 0}, age: {(datetime.now(timezone.utc) - datetime.fromtimestamp(submission.created_utc, timezone.utc)).days} days, num_comments: {submission.num_comments}, stickied: {submission.stickied})"
                    )
                    if submission.stickied:
                        skipped_stickied += 1
                        continue
                    if (
                        datetime.now(timezone.utc)
                        - datetime.fromtimestamp(submission.created_utc, timezone.utc)
                    ).days > 60:
                        skipped_old += 1
                        continue
                    if not submission.selftext:
                        if submission.num_comments > 20 and submission.score > 20:
                            pass
                        else:
                            skipped_no_selftext += 1
                            continue

                    # Check if already processed
                    if self.session:
                        existing_post = (
                            self.session.query(RedditPost)
                            .filter_by(post_id=submission.id)
                            .first()
                        )
                        if existing_post:
                            skipped_already_processed += 1
                            continue

                    # Return the submission without generating comment summary
                    # Comment summary will be generated when needed in the actual pipeline
                    logger.info(
                        f"Found suitable post {submission.id} after processing {processed_count} submissions"
                    )
                    return submission
                # If we reach here, no suitable post was found in this attempt
                logger.info(
                    f"Attempt {attempt + 1}/{tries} summary: processed {processed_count} submissions, "
                    f"skipped {skipped_stickied} stickied, {skipped_old} old, {skipped_no_selftext} no selftext, {skipped_already_processed} already processed"
                )
            return None
        except Exception as e:
            logger.error(f"Error finding top post: {str(e)}")
            return None
