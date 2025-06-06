from .base import ChannelAgent
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.models import Product, ContentType, DistributionStatus, DistributionMetadata
from app.distribution.reddit import RedditDistributionChannel, RedditDistributionError
import praw

logger = logging.getLogger(__name__)

class RedditAgent(ChannelAgent):
    """Reddit agent that behaves like a user to distribute content effectively."""

    def __init__(self, personality: Optional[Dict[str, Any]] = None):
        """Initialize the Reddit agent with personality traits and Reddit API client."""
        super().__init__()
        self.distribution_channel = RedditDistributionChannel()
        
        # Initialize PRAW Reddit client
        self.reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            username=os.getenv('REDDIT_USERNAME'),
            password=os.getenv('REDDIT_PASSWORD'),
            user_agent=os.getenv('REDDIT_USER_AGENT', 'zazzle-agent by u/yourusername')
        )
        
        # Default personality traits
        self.personality = personality or {
            'tone': 'helpful',  # helpful, enthusiastic, professional
            'interaction_style': 'community_focused',  # community_focused, informative, casual
            'posting_frequency': {
                'min_posts_per_day': 1,  # Minimum 1 post to maintain presence
                'max_posts_per_day': 3,  # Cap at 3 to avoid spam
                'preferred_hours': [10, 14, 18],  # Peak engagement hours
                'timezone': 'UTC'
            },
            'engagement_rules': {
                'max_posts_per_day': 3,
                'max_comments_per_day': 10,
                'max_upvotes_per_day': 50,
                'min_time_between_actions': 3600,  # 1 hour between actions
                'revenue_focus': {
                    'min_affiliate_links_per_day': 1,
                    'max_affiliate_links_per_day': 2,
                    'min_organic_content_per_day': 1,
                    'preferred_subreddits': [
                        'shopping',
                        'gadgets',
                        'deals',
                        'fashion',
                        'home'
                    ],
                    'engagement_ratio': 0.8  # 80% engagement, 20% promotion
                }
            }
        }
        
        # Track daily activity
        self.daily_stats = {
            'posts': 0,
            'comments': 0,
            'upvotes': 0,
            'affiliate_posts': 0,
            'organic_posts': 0,
            'last_action_time': None
        }
        self._reset_daily_stats_if_needed()

    def _reset_daily_stats_if_needed(self):
        """Reset daily statistics if it's a new day."""
        now = datetime.utcnow()
        if (not self.daily_stats['last_action_time'] or 
            (now - self.daily_stats['last_action_time']).days >= 1):
            self.daily_stats = {
                'posts': 0,
                'comments': 0,
                'upvotes': 0,
                'affiliate_posts': 0,
                'organic_posts': 0,
                'last_action_time': now
            }

    def _should_take_action(self, action_type: str) -> bool:
        """Check if agent should take action based on daily limits and timing."""
        self._reset_daily_stats_if_needed()
        
        # Check daily limits
        if action_type == 'post':
            if self.daily_stats['posts'] >= self.personality['engagement_rules']['max_posts_per_day']:
                return False
            # Check affiliate vs organic post balance
            if self.daily_stats['affiliate_posts'] >= self.personality['engagement_rules']['revenue_focus']['max_affiliate_links_per_day']:
                return False
        elif action_type == 'comment':
            if self.daily_stats['comments'] >= self.personality['engagement_rules']['max_comments_per_day']:
                return False
        elif action_type == 'upvote':
            if self.daily_stats['upvotes'] >= self.personality['engagement_rules']['max_upvotes_per_day']:
                return False

        # Check time between actions
        if self.daily_stats['last_action_time']:
            time_since_last = (datetime.utcnow() - self.daily_stats['last_action_time']).total_seconds()
            if time_since_last < self.personality['engagement_rules']['min_time_between_actions']:
                return False

        return True

    def _update_action_stats(self, action_type: str, is_affiliate: bool = False):
        """Update daily statistics after taking action."""
        if action_type == 'post':
            self.daily_stats['posts'] += 1
            if is_affiliate:
                self.daily_stats['affiliate_posts'] += 1
            else:
                self.daily_stats['organic_posts'] += 1
        elif action_type == 'comment':
            self.daily_stats['comments'] += 1
        elif action_type == 'upvote':
            self.daily_stats['upvotes'] += 1
        
        self.daily_stats['last_action_time'] = datetime.utcnow()

    def _format_content(self, product: Product) -> str:
        """Format content according to personality."""
        if not product.content:
            return ""

        base_content = product.content.strip()
        
        # Add personality-specific formatting
        if self.personality['tone'] == 'helpful':
            formatted = f"{base_content}\n\n"
            if product.affiliate_link:
                formatted += "You can find this product here: "
            formatted += f"#{product.name.replace(' ', '')} #Zazzle #Shopping"
        elif self.personality['tone'] == 'enthusiastic':
            formatted = f"🔥 {base_content} 🔥\n\n"
            if product.affiliate_link:
                formatted += "Check it out here 👉 "
            formatted += f"#{product.name.replace(' ', '')} #Zazzle #Shopping"
        else:  # professional
            formatted = f"{base_content}\n\n"
            if product.affiliate_link:
                formatted += "Product link: "
            formatted += f"#{product.name.replace(' ', '')} #Zazzle #Shopping"

        return formatted

    def publish_product(self, product: Product) -> DistributionMetadata:
        """Publish a product to Reddit."""
        if not self._should_take_action('post'):
            return DistributionMetadata(
                channel="reddit",
                status=DistributionStatus.FAILED,
                error_message="Daily post limit reached"
            )

        try:
            # Format content with personality
            formatted_content = self._format_content(product)
            
            # Mock post publication (replace with actual Reddit API call)
            post_id = f"mock_post_{int(time.time())}"
            post_url = f"https://reddit.com/r/mock_subreddit/comments/{post_id}"
            
            # Update stats
            self._update_action_stats('post', is_affiliate=bool(product.affiliate_link))
            
            return DistributionMetadata(
                channel="reddit",
                status=DistributionStatus.PUBLISHED,
                published_at=datetime.utcnow(),
                channel_id=post_id,
                channel_url=post_url
            )
        except Exception as e:
            return DistributionMetadata(
                channel="reddit",
                status=DistributionStatus.FAILED,
                error_message=str(e)
            )

    def engage_with_content(self, post_id: str, action_type: str) -> bool:
        """Engage with content (comment, upvote)."""
        if not self._should_take_action(action_type):
            return False

        try:
            # Mock engagement (replace with actual Reddit API call)
            self._update_action_stats(action_type)
            return True
        except Exception:
            return False

    def get_engagement_suggestions(self, product: Product) -> List[Dict[str, str]]:
        """Get suggestions for engaging with related content."""
        # Mock suggestions (replace with actual content discovery)
        return [
            {
                'post_id': 'mock_related_1',
                'action': 'comment',
                'reason': 'Related product discussion'
            },
            {
                'post_id': 'mock_related_2',
                'action': 'upvote',
                'reason': 'High engagement potential'
            }
        ]

    def post_content(self, product, content):
        # Simulate posting as a user, include affiliate link naturally
        logger.info(f"[RedditAgent] Posting to Reddit as user: {content}\nAffiliate Link: {product.affiliate_link}")
        return True

    def interact_with_votes(self, post_id: str) -> None:
        """Interact with a post by upvoting and downvoting."""
        try:
            # Upvote the post
            self.reddit.submission(id=post_id).upvote()
            logger.info(f"Upvoted post {post_id}")
            # Downvote the post
            self.reddit.submission(id=post_id).downvote()
            logger.info(f"Downvoted post {post_id}")
        except Exception as e:
            logger.error(f"Error interacting with votes for post {post_id}: {str(e)}")

    def interact_with_users(self, product_id: str) -> None:
        """Interact with users on Reddit for a given product."""
        try:
            # Fetch a trending post from r/golf
            subreddit = self.reddit.subreddit("golf")
            trending_post = next(subreddit.hot(limit=1), None)
            if trending_post:
                post_id = trending_post.id
                post_title = trending_post.title
                logger.info(f"Found trending post: {post_title} (ID: {post_id})")
                self.interact_with_votes(post_id)
            else:
                logger.warning("No trending post found in r/golf.")
        except Exception as e:
            logger.error(f"Error interacting with users for product {product_id}: {str(e)}") 