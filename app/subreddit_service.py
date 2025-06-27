"""
Subreddit service for managing subreddit entities and metadata.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.clients.reddit_client import RedditClient
from app.db.database import get_db
from app.db.models import Subreddit

logger = logging.getLogger(__name__)


class SubredditService:
    """Service for managing subreddit entities and metadata."""
    
    def __init__(self, reddit_client: RedditClient):
        self.reddit_client = reddit_client
    
    def get_or_create_subreddit(self, subreddit_name: str, db: Session) -> Subreddit:
        """
        Get an existing subreddit or create a new one with metadata from Reddit.
        
        Args:
            subreddit_name: The name of the subreddit (e.g., "golf", "all")
            db: Database session
            
        Returns:
            Subreddit entity
        """
        # Check if subreddit already exists
        existing = db.query(Subreddit).filter_by(subreddit_name=subreddit_name).first()
        if existing:
            return existing
        
        # Create new subreddit with metadata from Reddit
        return self._create_subreddit_with_metadata(subreddit_name, db)
    
    def _create_subreddit_with_metadata(self, subreddit_name: str, db: Session) -> Subreddit:
        """
        Create a new subreddit entity with metadata fetched from Reddit.
        
        Args:
            subreddit_name: The name of the subreddit
            db: Database session
            
        Returns:
            Newly created Subreddit entity
        """
        try:
            # Fetch metadata from Reddit
            subreddit_data = self._fetch_subreddit_metadata(subreddit_name)
            
            # Create subreddit entity
            subreddit = Subreddit(
                subreddit_name=subreddit_name,
                reddit_id=subreddit_data.get("id"),
                reddit_fullname=subreddit_data.get("name"),
                display_name=subreddit_data.get("display_name"),
                description=subreddit_data.get("description"),
                description_html=subreddit_data.get("description_html"),
                public_description=subreddit_data.get("public_description"),
                created_utc=self._parse_created_utc(subreddit_data.get("created_utc")),
                subscribers=subreddit_data.get("subscribers"),
                over18=subreddit_data.get("over18", False),
                spoilers_enabled=subreddit_data.get("spoilers_enabled", False),
            )
            
            db.add(subreddit)
            db.commit()
            db.refresh(subreddit)
            
            logger.info(f"Created subreddit entity for r/{subreddit_name}")
            return subreddit
            
        except Exception as e:
            logger.error(f"Failed to create subreddit entity for r/{subreddit_name}: {e}")
            # Create minimal subreddit entity without metadata
            subreddit = Subreddit(
                subreddit_name=subreddit_name,
                display_name=subreddit_name,
            )
            
            db.add(subreddit)
            db.commit()
            db.refresh(subreddit)
            
            logger.info(f"Created minimal subreddit entity for r/{subreddit_name}")
            return subreddit
    
    def _fetch_subreddit_metadata(self, subreddit_name: str) -> dict:
        """
        Fetch subreddit metadata from Reddit using PRAW.
        
        Args:
            subreddit_name: The name of the subreddit
            
        Returns:
            Dictionary containing subreddit metadata
        """
        try:
            # Get subreddit instance from PRAW
            subreddit = self.reddit_client.reddit.subreddit(subreddit_name)
            
            # Fetch metadata
            metadata = {
                "id": subreddit.id,
                "name": subreddit.name,
                "display_name": subreddit.display_name,
                "description": subreddit.description,
                "description_html": subreddit.description_html,
                "public_description": subreddit.public_description,
                "created_utc": subreddit.created_utc,
                "subscribers": subreddit.subscribers,
                "over18": subreddit.over18,
                "spoilers_enabled": subreddit.spoilers_enabled,
            }
            
            logger.info(f"Fetched metadata for r/{subreddit_name}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to fetch metadata for r/{subreddit_name}: {e}")
            raise
    
    def _parse_created_utc(self, created_utc: Optional[float]) -> Optional[datetime]:
        """
        Parse Reddit's created_utc timestamp to datetime.
        
        Args:
            created_utc: Unix timestamp from Reddit
            
        Returns:
            datetime object or None
        """
        if created_utc is None:
            return None
        
        try:
            return datetime.fromtimestamp(created_utc, tz=timezone.utc)
        except (ValueError, TypeError):
            logger.warning(f"Invalid created_utc timestamp: {created_utc}")
            return None
    
    def update_subreddit_metadata(self, subreddit_name: str, db: Session) -> Optional[Subreddit]:
        """
        Update existing subreddit metadata from Reddit.
        
        Args:
            subreddit_name: The name of the subreddit
            db: Database session
            
        Returns:
            Updated Subreddit entity or None if not found
        """
        subreddit = db.query(Subreddit).filter_by(subreddit_name=subreddit_name).first()
        if not subreddit:
            logger.warning(f"Subreddit r/{subreddit_name} not found for metadata update")
            return None
        
        try:
            # Fetch fresh metadata from Reddit
            metadata = self._fetch_subreddit_metadata(subreddit_name)
            
            # Update fields
            subreddit.reddit_id = metadata.get("id")
            subreddit.reddit_fullname = metadata.get("name")
            subreddit.display_name = metadata.get("display_name")
            subreddit.description = metadata.get("description")
            subreddit.description_html = metadata.get("description_html")
            subreddit.public_description = metadata.get("public_description")
            subreddit.created_utc = self._parse_created_utc(metadata.get("created_utc"))
            subreddit.subscribers = metadata.get("subscribers")
            subreddit.over18 = metadata.get("over18", False)
            subreddit.spoilers_enabled = metadata.get("spoilers_enabled", False)
            subreddit.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(subreddit)
            
            logger.info(f"Updated metadata for r/{subreddit_name}")
            return subreddit
            
        except Exception as e:
            logger.error(f"Failed to update metadata for r/{subreddit_name}: {e}")
            db.rollback()
            return None
    
    def get_subreddit_by_name(self, subreddit_name: str, db: Session) -> Optional[Subreddit]:
        """
        Get subreddit entity by name.
        
        Args:
            subreddit_name: The name of the subreddit
            db: Database session
            
        Returns:
            Subreddit entity or None if not found
        """
        return db.query(Subreddit).filter_by(subreddit_name=subreddit_name).first()
    
    def get_subreddit_by_id(self, subreddit_id: int, db: Session) -> Optional[Subreddit]:
        """
        Get subreddit entity by ID.
        
        Args:
            subreddit_id: The subreddit ID
            db: Database session
            
        Returns:
            Subreddit entity or None if not found
        """
        return db.query(Subreddit).filter_by(id=subreddit_id).first()


# Global instance for use throughout the application
def get_subreddit_service() -> SubredditService:
    """Get the global subreddit service instance."""
    return SubredditService(RedditClient()) 