"""
Data models for the Zazzle Agent application.

This module defines the core data structures used throughout the application,
including product information, Reddit context, distribution metadata, and more.
Each class is designed to be serializable and includes utility methods for
conversion between different formats (dict, JSON, CSV).

The module provides:
- Data models for product information and metadata
- Reddit context and content models
- Distribution tracking and status models
- Serialization utilities for various formats
- Logging and debugging support
"""

import csv
import json
import os
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


# Tier System Constants
class DonationTier(str, Enum):
    """Donation tiers based on amount."""
    BRONZE = "bronze"      # $1
    SILVER = "silver"      # $5
    GOLD = "gold"          # $10
    SAPPHIRE = "sapphire"  # $25
    DIAMOND = "diamond"    # $100


# Tier amount mappings
TIER_AMOUNTS = {
    DonationTier.BRONZE: Decimal("1.00"),
    DonationTier.SILVER: Decimal("5.00"),
    DonationTier.GOLD: Decimal("10.00"),
    DonationTier.SAPPHIRE: Decimal("25.00"),
    DonationTier.DIAMOND: Decimal("100.00"),
}

# Commission type minimum tier requirements
COMMISSION_MINIMUM_TIERS = {
    "specific_post": DonationTier.GOLD,      # $10 minimum
    "random_subreddit": DonationTier.SILVER,  # $5 minimum
    "random_random": DonationTier.BRONZE,     # $1 minimum
}


def get_tier_from_amount(amount: Decimal) -> DonationTier:
    """
    Determine the donation tier based on the amount.
    
    Args:
        amount: Donation amount in USD
        
    Returns:
        DonationTier: The appropriate tier for the amount
    """
    # Sort tiers by amount in descending order to find the highest applicable tier
    sorted_tiers = sorted(TIER_AMOUNTS.items(), key=lambda x: x[1], reverse=True)
    
    for tier, tier_amount in sorted_tiers:
        if amount >= tier_amount:
            return tier
    
    # If amount is less than Bronze minimum, return Bronze
    return DonationTier.BRONZE


def get_minimum_amount_for_tier(tier: DonationTier) -> Decimal:
    """
    Get the minimum amount required for a specific tier.
    
    Args:
        tier: The donation tier
        
    Returns:
        Decimal: Minimum amount required for the tier
    """
    return TIER_AMOUNTS.get(tier, Decimal("1.00"))


def validate_commission_tier(amount: Decimal, commission_type: str) -> bool:
    """
    Validate that the donation amount meets the minimum tier requirement for the commission type.
    
    Args:
        amount: Donation amount in USD
        commission_type: Type of commission being requested
        
    Returns:
        bool: True if amount meets minimum tier requirement
    """
    if commission_type not in COMMISSION_MINIMUM_TIERS:
        return False
    
    required_tier = COMMISSION_MINIMUM_TIERS[commission_type]
    required_amount = get_minimum_amount_for_tier(required_tier)
    
    return amount >= required_amount


# Pydantic schemas for API responses
class RedditPostSchema(BaseModel):
    id: int
    pipeline_run_id: int
    post_id: str
    title: str
    content: Optional[str] = None
    subreddit: str
    url: str
    permalink: Optional[str] = None
    comment_summary: Optional[str] = None
    author: Optional[str] = None
    score: Optional[int] = None
    num_comments: Optional[int] = None

    @field_validator("subreddit", mode="before")
    @classmethod
    def extract_subreddit_name(cls, value):
        """Extract subreddit name from relationship object if needed."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        # Handle SQLAlchemy relationship object
        if hasattr(value, 'subreddit_name'):
            return value.subreddit_name
        # Handle case where subreddit might be a different object
        if hasattr(value, '__class__') and 'Subreddit' in str(value.__class__):
            # Try to get subreddit_name attribute
            try:
                return getattr(value, 'subreddit_name', str(value))
            except:
                return str(value)
        return str(value)

    model_config = ConfigDict(from_attributes=True)


class PipelineRunSchema(BaseModel):
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str
    summary: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    duration: Optional[int] = None
    retry_count: int = Field(default=0)
    last_error: Optional[str] = None
    version: Optional[str] = None

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_datetime(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    model_config = ConfigDict(from_attributes=True)


class PipelineRunUsageSchema(BaseModel):
    id: int
    pipeline_run_id: int
    idea_model: str
    image_model: str
    prompt_tokens: int
    completion_tokens: int
    image_tokens: int
    total_cost_usd: Decimal
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_datetime(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    model_config = ConfigDict(from_attributes=True)


class ProductInfoSchema(BaseModel):
    id: int
    pipeline_run_id: int
    reddit_post_id: int
    theme: str
    image_title: Optional[str] = None
    image_url: str
    product_url: str
    affiliate_link: Optional[str] = None
    template_id: str
    model: str
    prompt_version: str
    product_type: str
    design_description: Optional[str] = None
    image_quality: str = "standard"
    available_actions: Optional[Dict[str, int]] = (
        None  # Maps action_type to remaining count
    )
    donation_info: Optional[Dict[str, Any]] = None  # Donation information if available

    model_config = ConfigDict(from_attributes=True)


class GeneratedProductSchema(BaseModel):
    product_info: ProductInfoSchema
    pipeline_run: PipelineRunSchema
    reddit_post: RedditPostSchema
    usage: Optional[PipelineRunUsageSchema] = None

    model_config = ConfigDict(from_attributes=True)


# SQLAlchemy Enums
class RedditPostStatus(Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class RedditCommentStatus(Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class ZazzleProductStatus(Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class ContentType(Enum):
    """
    Types of content that can be generated for a product.

    Currently supports:
        REDDIT: Content sourced from Reddit posts
    """

    REDDIT = "REDDIT"


class DistributionStatus(Enum):
    """
    Status of content distribution across channels.

    States:
        PENDING: Content is queued for distribution
        PUBLISHED: Content has been successfully published
        FAILED: Distribution attempt failed
    """

    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


@dataclass
class DistributionMetadata:
    """
    Metadata for content distribution to a specific channel.

    This class tracks the status and details of content distribution
    across different channels (e.g., social media platforms).

    Attributes:
        channel (str): The distribution channel name
        status (DistributionStatus): Current distribution status
        published_at (Optional[datetime]): Timestamp when content was published
        channel_id (Optional[str]): Platform-specific identifier (e.g., tweet ID)
        channel_url (Optional[str]): URL to the published content
        error_message (Optional[str]): Error details if distribution failed
    """

    channel: str
    status: DistributionStatus
    published_at: Optional[datetime] = None
    channel_id: Optional[str] = None  # e.g., tweet ID
    channel_url: Optional[str] = None  # e.g., tweet URL
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metadata to dictionary format.

        Returns:
            Dict[str, Any]: Dictionary representation of the metadata with datetime
                objects converted to ISO format strings.
        """
        data = {
            "channel": self.channel,
            "status": self.status.value,
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "channel_id": self.channel_id,
            "channel_url": self.channel_url,
            "error_message": self.error_message,
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DistributionMetadata":
        """
        Create metadata instance from dictionary.

        Args:
            data (Dict[str, Any]): Dictionary containing metadata fields

        Returns:
            DistributionMetadata: Instance with data from dictionary

        Note:
            Handles conversion of ISO format datetime strings back to datetime objects
        """
        published_at = None
        if data.get("published_at"):
            try:
                published_at = datetime.fromisoformat(data["published_at"])
            except ValueError:
                pass

        return cls(
            channel=data["channel"],
            status=DistributionStatus(data["status"]),
            published_at=published_at,
            channel_id=data.get("channel_id"),
            channel_url=data.get("channel_url"),
            error_message=data.get("error_message"),
        )


@dataclass
class PipelineConfig:
    """
    Configuration information used in main pipeline logic.

    This class holds configuration settings that control the behavior
    of the product creation pipeline.

    Attributes:
        model (str): The AI model to use (e.g. "dall-e-3")
        zazzle_template_id (str): The Zazzle template ID for product creation
        zazzle_tracking_code (str): The tracking code for Zazzle affiliate links
        zazzle_affiliate_id (str): The Zazzle affiliate ID for link generation
        prompt_version (str): Version of the prompt being used. Defaults to "1.0.0"
    """

    model: str
    zazzle_template_id: str
    zazzle_tracking_code: str
    zazzle_affiliate_id: str = os.getenv("ZAZZLE_AFFILIATE_ID", "")
    prompt_version: str = "1.0.0"
    image_quality: str = "standard"

    def log(self) -> None:
        """
        Log the configuration details to the application logger.

        Logs:
            - Model name
            - Template ID
            - Tracking code
            - Affiliate ID
            - Prompt version
        """
        logger.info("Pipeline Configuration:")
        logger.info(f"Model: {self.model}")
        logger.info(f"Template ID: {self.zazzle_template_id}")
        logger.info(f"Tracking Code: {self.zazzle_tracking_code}")
        logger.info(f"Affiliate ID: {self.zazzle_affiliate_id}")
        logger.info(f"Prompt Version: {self.prompt_version}")


@dataclass
class RedditContext:
    """
    Data generated by and relevant to the reddit agent.

    This class encapsulates all information related to a Reddit post
    that is being used as source material for product creation.

    Attributes:
        post_id (str): The Reddit post ID
        post_title (str): The title of the Reddit post
        post_url (str): The full URL to the Reddit post
        subreddit (str): The subreddit name
        post_content (Optional[str]): Optional content/body of the post
        comments (Optional[List[Dict[str, Any]]]): Optional list of comments on the post
        permalink (Optional[str]): The Reddit post's permalink
        author (Optional[str]): The Reddit post author
        score (Optional[int]): The Reddit post score (upvotes - downvotes)
        num_comments (Optional[int]): Number of comments on the post
    """

    post_id: str
    post_title: str
    post_url: str
    subreddit: str
    post_content: Optional[str] = None
    comments: Optional[List[Dict[str, Any]]] = None
    permalink: Optional[str] = None
    author: Optional[str] = None
    score: Optional[int] = None
    num_comments: Optional[int] = None

    def log(self) -> None:
        """
        Log the Reddit context details to the application logger.

        Logs:
            - Post ID and title
            - Post URL and subreddit
            - First 100 characters of content (if available)
            - Number of comments (if available)
            - Author and score (if available)
        """
        logger.info("Reddit Context:")
        logger.info(f"Post ID: {self.post_id}")
        logger.info(f"Title: {self.post_title}")
        logger.info(f"URL: {self.post_url}")
        logger.info(f"Subreddit: {self.subreddit}")
        if self.author:
            logger.info(f"Author: {self.author}")
        if self.score is not None:
            logger.info(f"Score: {self.score}")
        if self.num_comments is not None:
            logger.info(f"Number of comments: {self.num_comments}")
        if self.post_content:
            logger.info(f"Content: {self.post_content[:100]}...")  # Log first 100 chars
        if self.comments:
            logger.info(f"Number of comments: {len(self.comments)}")

    def to_schema(self) -> RedditPostSchema:
        """Convert to Pydantic schema for API responses."""
        return RedditPostSchema(
            id=0,  # This will be set by the ORM model
            pipeline_run_id=0,  # This will be set by the ORM model
            post_id=self.post_id,
            title=self.post_title,
            content=self.post_content,
            subreddit=self.subreddit,
            url=self.post_url,
            permalink=self.permalink,
            author=self.author,
            score=self.score,
            num_comments=self.num_comments,
        )


@dataclass
class ProductIdea:
    """
    Data about the product design process.

    This class represents the initial concept and design instructions
    for creating a product, including the source Reddit content.

    Attributes:
        theme (str): The main theme/idea for the product
        image_description (str): Description for image generation
        design_instructions (Dict[str, Any]): Instructions for product design
        reddit_context (RedditContext): The Reddit context this idea came from
        model (str): The AI model used
        prompt_version (str): Version of the prompt used
    """

    theme: str
    image_description: str
    design_instructions: Dict[str, Any]
    reddit_context: RedditContext
    model: str
    prompt_version: str

    def log(self) -> None:
        """
        Log the product idea details to the application logger.

        Logs:
            - Theme and image description
            - Model and prompt version
            - Design instructions
            - Reddit context details
        """
        logger.info("Product Idea:")
        logger.info(f"Theme: {self.theme}")
        logger.info(f"Image Description: {self.image_description}")
        logger.info(f"Model: {self.model}")
        logger.info(f"Prompt Version: {self.prompt_version}")
        logger.info("Design Instructions:")
        for key, value in self.design_instructions.items():
            logger.info(f"  {key}: {value}")
        self.reddit_context.log()


@dataclass
class ProductInfo:
    """
    The product data created by the ZazzleProductDesigner.

    This class represents a complete product with all its associated
    metadata, including design details, source information, and URLs.

    Attributes:
        product_id (str): Unique identifier for the product
        name (str): Product name
        product_type (str): Type of product (e.g. "sticker")
        image_url (str): URL to the product image
        product_url (str): URL to the Zazzle product page
        zazzle_template_id (str): The Zazzle template ID used
        zazzle_tracking_code (str): The tracking code used
        theme (str): The product theme
        model (str): The AI model used
        prompt_version (str): Version of the prompt used
        reddit_context (RedditContext): The Reddit context this product came from
        design_instructions (Dict[str, Any]): The design instructions used
        image_title (Optional[str]): Concise creative title for the image
        image_local_path (Optional[str]): Optional path to local image file
        affiliate_link (Optional[str]): Optional Zazzle affiliate link
    """

    product_id: str
    name: str
    product_type: str
    image_url: str
    product_url: str
    zazzle_template_id: str
    zazzle_tracking_code: str
    theme: str
    model: str
    prompt_version: str
    reddit_context: RedditContext
    design_instructions: Dict[str, Any]
    image_title: Optional[str] = None
    image_local_path: Optional[str] = None
    affiliate_link: Optional[str] = None
    image_quality: str = "standard"

    def log(self) -> None:
        """
        Log the product information to the application logger.

        Logs:
            - Product ID and name
            - Type and URLs
            - Template ID and theme
            - Model and prompt version
            - Local image path (if available)
            - Affiliate link (if available)
            - Reddit context details
        """
        logger.info("Product Information:")
        logger.info(f"ID: {self.product_id}")
        logger.info(f"Name: {self.name}")
        logger.info(f"Type: {self.product_type}")
        logger.info(f"Image URL: {self.image_url}")
        logger.info(f"Product URL: {self.product_url}")
        logger.info(f"Template ID: {self.zazzle_template_id}")
        logger.info(f"Theme: {self.theme}")
        logger.info(f"Model: {self.model}")
        logger.info(f"Prompt Version: {self.prompt_version}")
        if self.image_local_path:
            logger.info(f"Local Image Path: {self.image_local_path}")
        if self.affiliate_link:
            logger.info(f"Affiliate Link: {self.affiliate_link}")
        self.reddit_context.log()

    def to_csv(self, filename: str) -> None:
        """
        Save product data to CSV file.

        Args:
            filename (str): Path to the CSV file

        Note:
            If the file doesn't exist, it will be created with headers.
            If it exists, data will be appended to the existing file.
        """
        # Convert to dict and ensure all fields exist
        data = asdict(self)

        # Write to CSV
        file_exists = os.path.isfile(filename)
        with open(filename, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert product to dictionary format.

        Returns:
            Dict[str, Any]: Dictionary representation of the product with:
                - RedditContext converted to dict
                - datetime objects converted to ISO format strings
                - design_instructions serialized as JSON string
        """
        data = asdict(self)
        # Convert RedditContext to dict only if it's a dataclass instance
        if data.get("reddit_context") and is_dataclass(data["reddit_context"]):
            data["reddit_context"] = asdict(data["reddit_context"])
        # Convert datetime objects to strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        # Serialize design_instructions as JSON string
        if "design_instructions" in data and isinstance(
            data["design_instructions"], dict
        ):
            data["design_instructions"] = json.dumps(data["design_instructions"])
        return data

    def to_json(self) -> str:
        """
        Convert product to JSON string.

        Returns:
            str: JSON string representation of the product
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductInfo":
        """
        Create product instance from dictionary.

        Args:
            data (Dict[str, Any]): Dictionary containing product fields

        Returns:
            ProductInfo: Instance with data from dictionary

        Note:
            Handles conversion of RedditContext from dict back to object
        """
        if isinstance(data, ProductInfo):
            return data

        # Convert reddit_context dict back to RedditContext object
        reddit_context = data.get("reddit_context")
        if isinstance(reddit_context, dict):
            data["reddit_context"] = RedditContext(**reddit_context)

        return cls(**data)

    @staticmethod
    def generate_identifier(product_id: str) -> str:
        """
        Generate a unique identifier for a product.

        Args:
            product_id (str): Base product ID

        Returns:
            str: Unique identifier combining product ID and timestamp
        """
        return f"{product_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    def to_schema(self) -> ProductInfoSchema:
        """Convert to Pydantic schema for API responses."""
        return ProductInfoSchema(
            id=0,  # This will be set by the ORM model
            pipeline_run_id=0,  # This will be set by the ORM model
            reddit_post_id=0,  # This will be set by the ORM model
            theme=self.theme,
            image_title=self.image_title,
            image_url=self.image_url,
            product_url=self.product_url,
            affiliate_link=self.affiliate_link,
            template_id=self.zazzle_template_id,
            model=self.model,
            prompt_version=self.prompt_version,
            product_type=self.product_type,
            design_description=self.design_instructions.get("description"),
            available_actions=self.design_instructions.get("available_actions"),
            donation_info=self.design_instructions.get("donation_info"),
        )


@dataclass
class DesignInstructions:
    """
    Instructions for creating a product design.

    This class contains all the parameters needed to create a product
    design, including image, theme, text, and other customization options.

    Attributes:
        image (str): URL of the image to use
        theme (Optional[str]): Optional theme for the product
        image_title (Optional[str]): Optional concise creative title for the image
        text (Optional[str]): Optional text to include
        color (Optional[str]): Optional color specification
        quantity (Optional[int]): Optional quantity
        product_type (str): Type of product (e.g. "sticker"). Defaults to "sticker"
        template_id (Optional[str]): Optional template ID to use
        model (Optional[str]): Optional AI model used
        prompt_version (Optional[str]): Optional version of the prompt used
    """

    image: str
    theme: Optional[str] = None
    image_title: Optional[str] = None
    text: Optional[str] = None
    color: Optional[str] = None
    quantity: Optional[int] = None
    product_type: str = "sticker"
    template_id: Optional[str] = None
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    image_quality: str = "standard"


@dataclass
class AffiliateLinker:
    zazzle_affiliate_id: str
    zazzle_tracking_code: str

    def compose_affiliate_link(self, product_url: str) -> str:
        """
        Compose a Zazzle affiliate link with tracking code.

        Args:
            product_url (str): The base product URL

        Returns:
            str: Complete affiliate link with tracking code and affiliate ID
        """
        # Add tracking code if not present
        if "?" not in product_url:
            product_url += "?"
        elif not product_url.endswith("&"):
            product_url += "&"

        # Add tracking code and affiliate ID
        return (
            f"{product_url}rf={self.zazzle_affiliate_id}&tc={self.zazzle_tracking_code}"
        )


class InteractionActionType(str, Enum):
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"
    REPLY = "reply"


class InteractionTargetType(str, Enum):
    POST = "post"
    COMMENT = "comment"


class InteractionActionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class DonationStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    PROCESSING = "processing"
    REFUNDED = "refunded"


class DonationRequest(BaseModel):
    """Request model for creating a donation payment intent."""
    amount_usd: Decimal = Field(..., ge=0.50, le=10000.00, description="Amount in USD (minimum $0.50)")
    customer_email: Optional[str] = Field(None, max_length=255, description="Customer email address")
    customer_name: Optional[str] = Field(None, max_length=255, description="Customer name")
    message: Optional[str] = Field(None, max_length=1000, description="Optional message from donor")
    subreddit: Optional[str] = Field(None, max_length=100, description="Subreddit for the commission. Required for specific_post and random_subreddit, optional for random_random.")
    reddit_username: Optional[str] = Field(None, max_length=100, description="Reddit username of the donor (if blank, donation is anonymous)")
    is_anonymous: bool = Field(False, description="Whether the donation should be anonymous")
    donation_type: str = Field(..., description="Type of donation: 'commission' or 'support'")
    post_id: Optional[str] = Field(None, max_length=100, description="Reddit post ID (required for support donations, optional for commission)")
    commission_message: Optional[str] = Field(None, max_length=1000, description="Optional commission message (for commission donations)")
    commission_type: Optional[str] = Field(None, description="Type of commission: 'specific_post' or 'random_subreddit'")

    @field_validator('donation_type')
    @classmethod
    def validate_donation_type(cls, v):
        """Validate donation type."""
        if v not in ["commission", "support"]:
            raise ValueError("donation_type must be 'commission' or 'support'")
        return v
    
    @field_validator('commission_type')
    @classmethod
    def validate_commission_type(cls, v):
        """Validate commission type."""
        if v is not None and v not in ["specific_post", "random_subreddit", "random_random"]:
            raise ValueError("commission_type must be 'specific_post', 'random_subreddit', or 'random_random'")
        return v
    
    @model_validator(mode='after')
    def validate_post_id_for_support(self):
        """Validate that post_id is provided for support donations."""
        if self.donation_type == "support":
            if not self.post_id or self.post_id.strip() == "":
                raise ValueError("post_id is required for support donations")
        return self
    
    @model_validator(mode='after')
    def validate_commission_requirements(self):
        """Validate commission type and tier requirements."""
        if self.donation_type == "commission":
            if not self.commission_type:
                raise ValueError("commission_type is required for commission donations")
            # Validate tier requirements
            if not validate_commission_tier(self.amount_usd, self.commission_type):
                required_tier = COMMISSION_MINIMUM_TIERS[self.commission_type]
                required_amount = get_minimum_amount_for_tier(required_tier)
                raise ValueError(f"Commission type '{self.commission_type}' requires minimum {required_tier.value} tier (${required_amount})")
            # For all commission types, allow post_id to be provided (for new workflow)
            if self.commission_type == "random_random":
                pass  # No validation on subreddit or post_id for random_random
            elif self.commission_type == "random_subreddit":
                if not self.subreddit:
                    raise ValueError("subreddit is required for random_subreddit commissions")
            elif self.commission_type == "specific_post":
                if not self.subreddit:
                    raise ValueError("subreddit is required for specific_post commissions")
                if not self.post_id:
                    raise ValueError("post_id is required for specific_post commissions")
        return self
    
    # Removed automatic is_anonymous validation - let frontend control this
    # @field_validator('reddit_username')
    # @classmethod
    # def validate_anonymous_donation(cls, v, info):
    #     """Set is_anonymous to True if reddit_username is blank."""
    #     if not v:
    #         info.data['is_anonymous'] = True
    #     return v


class CommissionRequest(BaseModel):
    """Request model for commissioning a post."""
    amount_usd: Decimal = Field(..., ge=0.50, le=10000.00, description="Amount in USD (minimum $0.50)")
    customer_email: Optional[str] = Field(None, max_length=255, description="Customer email address")
    customer_name: Optional[str] = Field(None, max_length=255, description="Customer name")
    subreddit: str = Field(..., max_length=100, description="Subreddit to commission from")
    reddit_username: Optional[str] = Field(None, max_length=100, description="Reddit username of the donor")
    is_anonymous: bool = Field(False, description="Whether the commission should be anonymous")
    post_id: Optional[str] = Field(None, max_length=32, description="Reddit post ID for Gold/Platinum tiers")
    commission_message: Optional[str] = Field(None, max_length=500, description="Optional message to display with commission badge")


class SponsorRequest(BaseModel):
    """Request model for sponsoring an existing post."""
    amount_usd: Decimal = Field(..., ge=0.50, le=10000.00, description="Amount in USD (minimum $0.50)")
    customer_email: Optional[str] = Field(None, max_length=255, description="Customer email address")
    customer_name: Optional[str] = Field(None, max_length=255, description="Customer name")
    reddit_username: Optional[str] = Field(None, max_length=100, description="Reddit username of the donor")
    is_anonymous: bool = Field(False, description="Whether the sponsorship should be anonymous")
    post_id: str = Field(..., max_length=32, description="Reddit post ID to sponsor")
    sponsor_message: Optional[str] = Field(None, max_length=500, description="Optional message from sponsor")


class DonationResponse(BaseModel):
    """Response model for donation payment intent."""
    client_secret: str = Field(..., description="Stripe client secret for payment confirmation")
    payment_intent_id: str = Field(..., description="Stripe payment intent ID")


class DonationSchema(BaseModel):
    """Schema for donation data."""
    id: int
    stripe_payment_intent_id: str
    amount_cents: int
    amount_usd: Decimal
    currency: str
    status: DonationStatus
    tier: DonationTier
    customer_email: Optional[str]
    customer_name: Optional[str]
    message: Optional[str]
    subreddit: Optional[str]
    reddit_username: Optional[str]
    is_anonymous: bool
    donation_type: str
    commission_type: Optional[str]
    post_id: Optional[str]
    commission_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    @field_validator("subreddit", mode="before")
    @classmethod
    def extract_subreddit_name(cls, value):
        """Extract subreddit name from relationship object if needed."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        # Handle SQLAlchemy relationship object
        if hasattr(value, 'subreddit_name'):
            return value.subreddit_name
        # Handle case where subreddit might be a different object
        if hasattr(value, '__class__') and 'Subreddit' in str(value.__class__):
            # Try to get subreddit_name attribute
            try:
                return getattr(value, 'subreddit_name', str(value))
            except:
                return str(value)
        return str(value)

    class Config:
        from_attributes = True


class DonationSummary(BaseModel):
    """Summary of donation statistics."""
    total_donations: int
    total_amount_usd: Decimal
    total_donors: int
    recent_donations: List[DonationSchema]


class CheckoutSessionResponse(BaseModel):
    """Response model for Stripe Checkout session creation."""
    session_id: str
    url: str


class CommissionValidationRequest(BaseModel):
    """Request model for validating commission parameters."""
    commission_type: str = Field(..., description="Type of commission: 'random_subreddit', 'specific_post', or 'random_random'")
    subreddit: Optional[str] = Field(None, max_length=100, description="Subreddit name (required for random_subreddit and specific_post)")
    post_id: Optional[str] = Field(None, max_length=32, description="Reddit post ID (required for specific_post)")

    @field_validator('commission_type')
    @classmethod
    def validate_commission_type(cls, v):
        """Validate commission type."""
        valid_types = ['random_subreddit', 'specific_post', 'random_random']
        if v not in valid_types:
            raise ValueError(f'commission_type must be one of: {valid_types}')
        return v

    @model_validator(mode='after')
    def validate_required_fields(self):
        """Validate required fields based on commission type."""
        if self.commission_type in ['random_subreddit', 'specific_post']:
            if not self.subreddit:
                raise ValueError(f'subreddit is required for {self.commission_type} commission type')
        
        if self.commission_type == 'specific_post':
            if not self.post_id:
                raise ValueError('post_id is required for specific_post commission type')
        
        return self


class CommissionValidationResponse(BaseModel):
    """Response model for commission validation."""
    valid: bool = Field(..., description="Whether the commission parameters are valid")
    subreddit: Optional[str] = Field(None, description="Validated subreddit name")
    subreddit_id: Optional[int] = Field(None, description="Database ID of the subreddit")
    post_id: Optional[str] = Field(None, description="Validated post ID")
    post_title: Optional[str] = Field(None, description="Title of the post")
    post_content: Optional[str] = Field(None, description="Content of the post")
    post_url: Optional[str] = Field(None, description="URL of the post")
    commission_type: str = Field(..., description="Type of commission that was validated")
    error: Optional[str] = Field(None, description="Error message if validation failed")


class ProductSubredditPostSchema(BaseModel):
    """Schema for tracking products published to subreddits."""
    id: int
    product_info_id: int
    subreddit_name: str
    reddit_post_id: str
    reddit_post_url: Optional[str] = None
    reddit_post_title: Optional[str] = None
    submitted_at: datetime
    dry_run: bool
    status: str
    error_message: Optional[str] = None
    engagement_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
