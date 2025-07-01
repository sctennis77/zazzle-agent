"""
Commission validation service for upstream validation of commission requests.

This service validates commission requests before payment processing to ensure
we have valid subreddit and post data before creating pipeline tasks.
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.clients.reddit_client import RedditClient
from app.agents.reddit_agent import RedditAgent, pick_subreddit
from app.db.database import SessionLocal
from app.db.models import Subreddit
from app.models import PipelineConfig, RedditContext
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class ValidationResult:
    """Result of commission validation."""
    
    def __init__(
        self,
        valid: bool,
        subreddit: Optional[str] = None,
        subreddit_id: Optional[int] = None,
        post_id: Optional[str] = None,
        post_title: Optional[str] = None,
        post_url: Optional[str] = None,
        post_content: Optional[str] = None,
        commission_type: Optional[str] = None,
        error: Optional[str] = None
    ):
        self.valid = valid
        self.subreddit = subreddit
        self.subreddit_id = subreddit_id
        self.post_id = post_id
        self.post_title = post_title
        self.post_url = post_url
        self.post_content = post_content
        self.commission_type = commission_type
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "valid": self.valid,
            "subreddit": self.subreddit,
            "subreddit_id": self.subreddit_id,
            "post_id": self.post_id,
            "post_title": self.post_title,
            "post_url": self.post_url,
            "post_content": self.post_content,
            "commission_type": self.commission_type,
            "error": self.error
        }


class CommissionValidator:
    """Service for validating commission requests before payment processing."""
    
    def __init__(self, session: Optional[Session] = None):
        self.session = session or SessionLocal()
        self.reddit_client = RedditClient()
        
        # Initialize RedditAgent for post finding and validation
        config = PipelineConfig(
            model="dall-e-3",
            zazzle_template_id="test_template",
            zazzle_tracking_code="test_code",
            zazzle_affiliate_id="test_affiliate",
            prompt_version="1.0.0"
        )
        self.reddit_agent = RedditAgent(
            config=config,
            pipeline_run_id=None,
            session=self.session
        )
    
    async def validate_commission(
        self,
        commission_type: str,
        subreddit: Optional[str] = None,
        post_id: Optional[str] = None,
        post_url: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate a commission request and return validated data.
        
        Args:
            commission_type: Type of commission (random_random, random_subreddit, specific_post)
            subreddit: Subreddit name (for random_subreddit)
            post_id: Reddit post ID (for specific_post)
            post_url: Reddit post URL (alternative for specific_post)
            
        Returns:
            ValidationResult: Validation result with subreddit and post data
        """
        try:
            logger.info(f"Validating commission: type={commission_type}, subreddit={subreddit}, post_id={post_id}")
            
            # Step 1: Handle random_random - pick random subreddit
            if commission_type == "random_random":
                return await self._validate_random_random()
            
            # Step 2: Handle random_subreddit - validate subreddit and find post
            elif commission_type == "random_subreddit":
                if not subreddit:
                    return ValidationResult(valid=False, error="Subreddit is required for random_subreddit commission")
                return await self._validate_random_subreddit(subreddit)
            
            # Step 3: Handle specific_post - validate specific post
            elif commission_type == "specific_post":
                if not post_id and not post_url:
                    return ValidationResult(valid=False, error="Post ID or URL is required for specific_post commission")
                return await self._validate_specific_post(post_id, post_url)
            
            else:
                return ValidationResult(valid=False, error=f"Unknown commission type: {commission_type}")
                
        except Exception as e:
            logger.error(f"Error validating commission: {str(e)}")
            return ValidationResult(valid=False, error=f"Validation error: {str(e)}")
    
    async def _validate_post(self, subreddit_name: str, post_id: str, commission_type: str) -> ValidationResult:
        """Validate a post given subreddit and post_id."""
        try:
            post = self.reddit_client.get_post(post_id)
            if not post:
                return ValidationResult(valid=False, error=f"Post {post_id} not found")
            # Extract info from PRAW Submission
            title = getattr(post, 'title', '')
            content = getattr(post, 'selftext', '')
            url = f"https://reddit.com{getattr(post, 'permalink', '')}"
            if not title or len(title.strip()) < 10:
                return ValidationResult(valid=False, error="Post title too short or missing")
            subreddit_id = self._get_subreddit_id(subreddit_name)
            return ValidationResult(
                valid=True,
                subreddit=subreddit_name,
                subreddit_id=subreddit_id,
                post_id=post_id,
                post_title=title,
                post_url=url,
                post_content=content,
                commission_type=commission_type
            )
        except Exception as e:
            logger.error(f"Error validating post {post_id}: {str(e)}")
            return ValidationResult(valid=False, error=f"Failed to validate post {post_id}: {str(e)}")
    
    async def _validate_random_random(self) -> ValidationResult:
        try:
            subreddit_name = pick_subreddit()
            logger.info(f"Selected random subreddit: {subreddit_name}")
            submission = await self.reddit_agent._find_trending_post_for_task()
            if not submission:
                return ValidationResult(valid=False, error=f"No trending posts found in r/{subreddit_name}")
            return await self._validate_post(subreddit_name, submission.id, "random_random")
        except Exception as e:
            logger.error(f"Error in random_random validation: {str(e)}")
            return ValidationResult(valid=False, error=f"Failed to find trending post in random subreddit: {str(e)}")
    
    async def _validate_random_subreddit(self, subreddit_name: str) -> ValidationResult:
        try:
            if not self._validate_subreddit_exists(subreddit_name):
                return ValidationResult(valid=False, error=f"Subreddit r/{subreddit_name} not found or not accessible")
            submission = await self.reddit_agent._find_trending_post_for_task()
            if not submission:
                return ValidationResult(valid=False, error=f"No trending posts found in r/{subreddit_name}")
            return await self._validate_post(subreddit_name, submission.id, "random_subreddit")
        except Exception as e:
            logger.error(f"Error in random_subreddit validation: {str(e)}")
            return ValidationResult(valid=False, error=f"Failed to find trending post in r/{subreddit_name}: {str(e)}")
    
    async def _validate_specific_post(self, post_id: Optional[str], post_url: Optional[str]) -> ValidationResult:
        try:
            if post_url and not post_id:
                post_id = self._extract_post_id_from_url(post_url)
                if not post_id:
                    return ValidationResult(valid=False, error="Could not extract post ID from URL")
            if not post_id:
                return ValidationResult(valid=False, error="Post ID is required")
            # Fetch the post to get subreddit name
            post = self.reddit_client.get_post(post_id)
            if not post:
                return ValidationResult(valid=False, error=f"Post {post_id} not found")
            subreddit_name = post.subreddit.display_name if post.subreddit else None
            if not subreddit_name:
                return ValidationResult(valid=False, error=f"Could not determine subreddit for post {post_id}")
            # Use the unified post validation method
            return await self._validate_post(subreddit_name, post_id, "specific_post")
        except Exception as e:
            logger.error(f"Error in specific_post validation: {str(e)}")
            return ValidationResult(valid=False, error=f"Failed to validate specific post: {str(e)}")
    
    def _validate_subreddit_exists(self, subreddit_name: str) -> bool:
        """Check if subreddit exists and is accessible."""
        try:
            # Try to get subreddit info from Reddit
            subreddit_info = self.reddit_client.get_subreddit(subreddit_name)
            return subreddit_info is not None
        except Exception as e:
            logger.warning(f"Error validating subreddit {subreddit_name}: {str(e)}")
            return False
    
    def _get_subreddit_id(self, subreddit_name: str) -> Optional[int]:
        """Get subreddit ID from database or create if doesn't exist."""
        try:
            subreddit = self.session.query(Subreddit).filter_by(subreddit_name=subreddit_name).first()
            if not subreddit:
                # Create subreddit if it doesn't exist
                subreddit = Subreddit(subreddit_name=subreddit_name)
                self.session.add(subreddit)
                self.session.commit()
                self.session.refresh(subreddit)
            
            return subreddit.id
            
        except Exception as e:
            logger.error(f"Error getting subreddit ID for {subreddit_name}: {str(e)}")
            return None
    
    def _extract_post_id_from_url(self, url: str) -> Optional[str]:
        """Extract post ID from Reddit URL."""
        try:
            # Handle various Reddit URL formats
            if 'reddit.com' in url:
                # Extract post ID from URL like https://reddit.com/r/subreddit/comments/abc123/title
                parts = url.split('/')
                for i, part in enumerate(parts):
                    if part == 'comments' and i + 1 < len(parts):
                        return parts[i + 1]
            
            # If it's already a post ID
            if len(url) == 6:  # Reddit post IDs are typically 6 characters
                return url
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting post ID from URL {url}: {str(e)}")
            return None 