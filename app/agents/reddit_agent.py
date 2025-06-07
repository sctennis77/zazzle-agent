from .base import ChannelAgent
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from app.models import Product, ContentType, DistributionStatus, DistributionMetadata
from app.distribution.reddit import RedditDistributionChannel, RedditDistributionError
import praw
from app.product_designer import ZazzleProductDesigner

logger = logging.getLogger(__name__)

class RedditAgent(ChannelAgent):
    """Reddit agent that behaves like a user to distribute content effectively."""

    def __init__(self, personality: Optional[Dict[str, Any]] = None, subreddit_name: str = None):
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

        self.subreddit_name = subreddit_name
        self.product_designer = ZazzleProductDesigner()

    def _reset_daily_stats_if_needed(self):
        """Reset daily statistics if it's a new day."""
        now = datetime.now(timezone.utc)
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
            time_since_last = (datetime.now(timezone.utc) - self.daily_stats['last_action_time']).total_seconds()
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
        
        self.daily_stats['last_action_time'] = datetime.now(timezone.utc)

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
                published_at=datetime.now(timezone.utc),
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

    def get_product_info(self, design_instructions: Dict[str, Any]) -> Dict[str, Any]:
        """Get product information from the Zazzle Product Designer Agent."""
        return self.product_designer.create_product(design_instructions)

    def interact_with_subreddit(self, product_info: Dict[str, Any]):
        """Interact with the subreddit to promote the product."""
        # Example interaction logic
        subreddit = self.reddit.subreddit(self.subreddit_name)
        # Post the product information to the subreddit
        subreddit.submit(
            title=f"Check out this custom golf ball: {product_info['product_id']}",
            selftext=f"Here's a link to the product: {product_info['product_url']}"
        )

    def _determine_product_idea(self, post_title: str, post_content: str = None, comments: List[Dict] = None) -> Optional[Dict]:
        """
        Analyze Reddit content to determine product ideas.
        
        Args:
            post_title: The title of the Reddit post
            post_content: The content/body of the Reddit post
            comments: List of top comments with their content
            
        Returns:
            Dict containing product idea details or None if no suitable idea is found
        """
        try:
            # Combine all content for analysis
            content_to_analyze = [post_title]
            if post_content:
                content_to_analyze.append(post_content)
            if comments:
                content_to_analyze.extend([comment.get('body', '') for comment in comments[:5]])  # Use top 5 comments
            
            # Analyze the content to identify themes, jokes, or interesting phrases
            # For now, we'll use a simple approach - later we can integrate with GPT for better analysis
            combined_content = ' '.join(content_to_analyze).lower()
            
            # Look for golf-related themes
            golf_themes = {
                'tournament': ['tournament', 'championship', 'open', 'masters', 'pga'],
                'jokes': ['joke', 'funny', 'meme', 'humor'],
                'tips': ['tip', 'advice', 'help', 'how to'],
                'equipment': ['club', 'driver', 'putter', 'ball', 'equipment'],
                'achievement': ['hole in one', 'eagle', 'birdie', 'par']
            }
            
            # Determine the main theme
            main_theme = None
            for theme, keywords in golf_themes.items():
                if any(keyword in combined_content for keyword in keywords):
                    main_theme = theme
                    break
            
            if not main_theme:
                return None
            
            # Generate appropriate text based on the theme
            if main_theme == 'tournament':
                text = f"🏆 {post_title} 🏆"
            elif main_theme == 'jokes':
                # Extract the joke or funny content
                text = post_title if 'joke' in post_title.lower() else "Golf Joke"
            elif main_theme == 'tips':
                text = "Golf Pro Tip"
            elif main_theme == 'equipment':
                text = "Golf Equipment"
            elif main_theme == 'achievement':
                text = "Golf Achievement"
            else:
                text = "Golf Ball"
            
            return {
                'text': text,
                'color': 'Blue',  # Default color
                'quantity': 12,   # Default quantity
                'theme': main_theme
            }
            
        except Exception as e:
            logger.error(f"Error determining product idea: {str(e)}")
            return None

    def find_and_create_product(self) -> Optional[Dict]:
        """Find a post on r/golf and create a custom golf ball product."""
        try:
            # Get the r/golf subreddit
            subreddit = self.reddit.subreddit('golf')
            
            # Get the top post and its comments
            for post in subreddit.hot(limit=1):
                # Get top comments
                post.comments.replace_more(limit=0)  # Don't load more comments
                top_comments = [
                    {
                        'id': comment.id,
                        'body': comment.body,
                        'score': comment.score
                    }
                    for comment in post.comments.list()[:5]  # Get top 5 comments
                ]
                
                # Determine product idea based on post content and comments
                product_info = self._determine_product_idea(
                    post_title=post.title,
                    post_content=post.selftext,
                    comments=top_comments
                )
                
                if not product_info:
                    continue
                
                # Add Reddit context
                product_info.update({
                    'reddit_context': {
                        'type': 'post',
                        'id': post.id,
                        'title': post.title,
                        'url': f'https://reddit.com{post.permalink}',
                        'created_utc': post.created_utc,
                        'theme': product_info.get('theme')
                    },
                    'image_url': 'https://via.placeholder.com/150',  # This URL is for internal tracking, not direct Zazzle pre-population
                    'image_iid': '4b2bbb87-ee28-47a3-9de9-5ddb045ec8bc' # Placeholder IID from your screenshot. This will be replaced by actual generated Zazzle Image IDs later.
                })
                
                # Create the product using Zazzle's CAP system
                product_designer = ZazzleProductDesigner()
                created_product = product_designer.create_product(product_info)
                
                if created_product:
                    # Add the product URL to the info
                    product_info['product_url'] = created_product.get('product_url', '')
                    return product_info
                
                return None
                
        except Exception as e:
            logger.error(f"Error in find_and_create_product: {str(e)}")
            return None 