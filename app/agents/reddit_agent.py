"""
Reddit agent module for the Zazzle Agent application.

This module defines the RedditAgent, which automates content distribution, product idea generation,
image creation, and engagement on Reddit. It integrates with OpenAI, PRAW, and Zazzle product workflows.
"""

from .base import ChannelAgent
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from app.models import ProductInfo, RedditContext, ProductIdea, PipelineConfig, DistributionStatus, DistributionMetadata, DesignInstructions
from app.distribution.reddit import RedditDistributionChannel, RedditDistributionError
import praw
from app.zazzle_product_designer import ZazzleProductDesigner
import openai
import json
from app.image_generator import ImageGenerator
from app.utils.logging_config import get_logger
from dataclasses import asdict
from app.zazzle_templates import ZAZZLE_STICKER_TEMPLATE
from app.db.mappers import reddit_context_to_db

logger = get_logger(__name__)

class RedditAgent(ChannelAgent):
    """
    Reddit agent that behaves like a user to distribute content effectively.
    
    This agent can:
    - Analyze Reddit posts to generate product ideas
    - Generate images using OpenAI DALL-E
    - Create Zazzle products
    - Post and interact on Reddit
    - Track daily engagement statistics
    """

    def __init__(self, config_or_model: Any = None, subreddit_name='golf', pipeline_run_id=None, session=None):
        """
        Initialize the Reddit agent with configuration or model string.
        Optionally accepts pipeline_run_id and session for DB persistence.
        
        Args:
            config_or_model: PipelineConfig dict or model string (for backward compatibility)
            subreddit_name: Optional subreddit to target, defaults to 'golf'
            pipeline_run_id: Optional pipeline run ID for DB persistence
            session: Optional SQLAlchemy session for DB persistence
        """
        super().__init__()
        # Support both config dict and model string for backward compatibility in tests
        if isinstance(config_or_model, dict):
            model = config_or_model.get('model', 'dall-e-3')
            self.personality = config_or_model.get('personality', {})
            self.daily_stats = config_or_model.get('daily_stats', {
                'posts': 0,
                'comments': 0,
                'upvotes': 0,
                'affiliate_posts': 0,
                'organic_posts': 0,
                'last_action_time': None
            })
        elif isinstance(config_or_model, str):
            model = config_or_model
        else:
            model = 'dall-e-3'
        self.config = PipelineConfig(
            model=model,
            zazzle_template_id=ZAZZLE_STICKER_TEMPLATE.zazzle_template_id,
            zazzle_tracking_code=ZAZZLE_STICKER_TEMPLATE.zazzle_tracking_code,
            prompt_version="1.0.0"
        )
        self.image_generator = ImageGenerator(model=model)
        self.product_designer = ZazzleProductDesigner()
        if not hasattr(self, 'daily_stats'):
            self.daily_stats = {
                'posts': 0,
                'comments': 0,
                'upvotes': 0,
                'affiliate_posts': 0,
                'organic_posts': 0,
                'last_action_time': None
            }
        self.openai = openai
        
        # Initialize Reddit client
        self.reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT', 'zazzle-agent/1.0'),
            username=os.getenv('REDDIT_USERNAME'),
            password=os.getenv('REDDIT_PASSWORD')
        )
        self.subreddit_name = subreddit_name
        self.subreddit = self.reddit.subreddit(self.subreddit_name)
        # New: store pipeline_run_id and session for DB persistence
        self.pipeline_run_id = pipeline_run_id
        self.session = session

    def _determine_product_idea(self, reddit_context: RedditContext) -> Optional[ProductIdea]:
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
            response = self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a creative product idea generator for Zazzle or other platforms. Generate unique, innovative, marketable, and artistic product designs based Reddit posts. Keep image descriptions simple and focused on the key visual elements. Avoid complex details or too many elements. Focus on one main subject and the natural scenery (when applicable)."},
                    {"role": "user", "content": f"Based on this Reddit post:\nTitle: {reddit_context.post_title}\nContent: {reddit_context.post_content}\n\nGenerate a product idea with the following format:\nTheme: [Your creative theme here]\nImage Description: [A simple, clear description of the desired image content]"}
                ]
            )

            # Log the raw response for debugging
            logger.info(f"Raw OpenAI Response: {response.choices[0].message.content}")

            # Parse response to get theme and image description
            content = response.choices[0].message.content or ""
            lines = content.split('\n')
            logger.info(f"OpenAI Response: {lines}")
            theme = None
            image_description = None
            for line in lines:
                if line.startswith('Theme:'):
                    theme = line.replace('Theme:', '').strip().strip('"')
                elif line.startswith('Image Description:'):
                    image_description = line.replace('Image Description:', '').strip()

            # Treat empty strings as missing
            if not theme or not theme.strip():
                error_msg = "No theme found in OpenAI response"
                logger.error(error_msg)
                return None
            if not image_description or not image_description.strip():
                error_msg = "No image description found in OpenAI response"
                logger.error(error_msg)
                raise ValueError(error_msg)

            if theme.lower() == 'default theme':
                error_msg = "Invalid theme: 'default theme' is not allowed"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Create product idea
            product_idea = ProductIdea(
                theme=theme,
                image_description=image_description,
                design_instructions={
                    "image": None,
                    "theme": theme
                },
                reddit_context=reddit_context,
                model=self.config.model,
                prompt_version=self.config.prompt_version
            )

            return product_idea

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error determining product idea: {str(e)}")
            return None

    async def find_and_create_product(self) -> Optional[ProductInfo]:
        """
        Find a trending post and create a product from it.
        Persists RedditContext as RedditPost in the DB if session and pipeline_run_id are provided.
        Returns:
            ProductInfo object if successful, None otherwise
        """
        try:
            # Find a trending post
            trending_post = await self._find_trending_post()
            if not trending_post:
                logger.warning("No suitable trending post found")
                return None

            # Log trending post details
            logger.info("Found trending post:")
            logger.info(f"Post ID: {trending_post.id}")
            logger.info(f"Title: {trending_post.title}")
            logger.info(f"URL: {trending_post.url}")
            logger.info(f"Subreddit: {trending_post.subreddit.display_name}")
            logger.info(f"Content: {trending_post.selftext if hasattr(trending_post, 'selftext') else 'No content'}")
            logger.info(f"Comment Summary: {getattr(trending_post, 'comment_summary', 'No comment summary')}")

            # Create RedditContext from the post
            reddit_context = RedditContext(
                post_id=trending_post.id,
                post_title=trending_post.title,
                post_url=f"https://reddit.com{trending_post.permalink}",
                subreddit=trending_post.subreddit.display_name,
                post_content=trending_post.selftext if hasattr(trending_post, 'selftext') else None,
                comments=[{'text': getattr(trending_post, 'comment_summary', 'No comment summary')}]
            )

            # Determine product idea from post (synchronous call)
            product_idea = self._determine_product_idea(reddit_context)
            if not product_idea:
                logger.warning("Could not determine product idea from post")
                return None
            if not product_idea.theme or product_idea.theme.lower() == 'default theme':
                raise ValueError("No valid theme was generated from the Reddit context")
            logger.info(f"Product Idea: {product_idea}")
            if not product_idea.image_description or not product_idea.image_description.strip():
                logger.error("Image prompt (image_description) is empty. Aborting image generation.")
                raise ValueError("Image prompt (image_description) cannot be empty.")
            try:
                imgur_url, local_path = await self.image_generator.generate_image(
                    product_idea.image_description,
                    template_id=self.config.zazzle_template_id
                )
            except Exception as e:
                logger.error(f"Failed to generate image: {str(e)}")
                return None
            design_instructions = DesignInstructions(
                image=imgur_url,
                theme=product_idea.theme,
                text=product_idea.image_description,
                product_type='sticker',
                template_id=self.config.zazzle_template_id,
                model=self.config.model,
                prompt_version=self.config.prompt_version
            )
            logger.info(f"Design Instructions: {design_instructions}")
            product_info = await self.product_designer.create_product(
                design_instructions=design_instructions,
                reddit_context=reddit_context
            )
            if not product_info:
                logger.warning("Failed to create product")
                return None
            if isinstance(product_info, dict):
                product_info = ProductInfo.from_dict(product_info)
            return product_info
        except Exception as e:
            logger.error(f"Error in find_and_create_product: {str(e)}")
            return None

    def save_reddit_context_to_db(self, reddit_context) -> Optional[int]:
        """
        Persist a RedditContext as RedditPost in the DB and return the DB ID.
        
        Returns:
            int: The ID of the persisted RedditPost if successful
            None: If persistence fails or no session/pipeline_run_id is provided
        """
        from app.db.mappers import reddit_context_to_db
        reddit_post_id = None
        if self.session and self.pipeline_run_id:
            try:
                orm_post = reddit_context_to_db(reddit_context, self.pipeline_run_id)
                self.session.add(orm_post)
                self.session.commit()
                reddit_post_id = orm_post.id
                logger.info(f"Persisted RedditPost with id {reddit_post_id}")
            except Exception as e:
                logger.error(f"Failed to persist RedditPost: {str(e)}")
                self.session.rollback()
                return None
        return reddit_post_id

    def _reset_daily_stats_if_needed(self):
        """
        Reset daily statistics if it's a new day.
        """
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
        """
        Check if agent should take action based on daily limits and timing.
        """
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

    def _format_content(self, product_info: ProductInfo) -> str:
        """Format content according to personality."""
        if not product_info.design_instructions.get('content'):
            return ""

        base_content = product_info.design_instructions['content'].strip()
        
        # Add personality-specific formatting
        if self.personality['tone'] == 'helpful':
            formatted = f"{base_content}\n\n"
            if product_info.affiliate_link:
                formatted += "You can find this product here: "
            formatted += f"#{product_info.name.replace(' ', '')} #Zazzle #Shopping"
        elif self.personality['tone'] == 'enthusiastic':
            formatted = f"🔥 {base_content} 🔥\n\n"
            if product_info.affiliate_link:
                formatted += "Check it out here 👉 "
            formatted += f"#{product_info.name.replace(' ', '')} #Zazzle #Shopping"
        else:  # professional
            formatted = f"{base_content}\n\n"
            if product_info.affiliate_link:
                formatted += "Product link: "
            formatted += f"#{product_info.name.replace(' ', '')} #Zazzle #Shopping"

        return formatted

    def publish_product(self, product_info: ProductInfo) -> DistributionMetadata:
        """Publish a product to Reddit."""
        if not self._should_take_action('post'):
            return DistributionMetadata(
                channel="reddit",
                status=DistributionStatus.FAILED,
                error_message="Daily post limit reached"
            )

        try:
            # Format content with personality
            formatted_content = self._format_content(product_info)
            
            # Mock post publication (replace with actual Reddit API call)
            post_id = f"mock_post_{int(time.time())}"
            post_url = f"https://reddit.com/r/mock_subreddit/comments/{post_id}"
            
            # Update stats
            self._update_action_stats('post', is_affiliate=bool(product_info.affiliate_link))
            
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
        except Exception as e:
            logger.error(f"Error engaging with content: {str(e)}")
            return False

    def get_engagement_suggestions(self, product_info: ProductInfo) -> List[Dict[str, str]]:
        """Get suggestions for engaging with content."""
        suggestions = []
        if self._should_take_action('comment'):
            suggestions.append({
                'type': 'comment',
                'text': self._generate_engaging_comment(product_info.design_instructions)
            })
        if self._should_take_action('upvote'):
            suggestions.append({
                'type': 'upvote',
                'text': 'Upvote the post'
            })
        return suggestions

    def post_content(self, product_info: ProductInfo, content: str):
        """Simulate posting as a user, include affiliate link naturally."""
        if not self._should_take_action('post'):
            return False

        try:
            # Mock post (replace with actual Reddit API call)
            self._update_action_stats('post', is_affiliate=bool(product_info.affiliate_link))
            return True
        except Exception as e:
            logger.error(f"Error posting content: {str(e)}")
            return False

    def interact_with_votes(self, post_id: str, comment_id: str = None) -> Dict[str, str]:
        """Interact with votes on a post or comment."""
        if not self._should_take_action('upvote'):
            return {'type': 'vote', 'action': 'skipped', 'reason': 'Daily limit reached'}

        try:
            # Mock vote (replace with actual Reddit API call)
            self._update_action_stats('upvote')
            return {'type': 'vote', 'action': 'upvoted'}
        except Exception as e:
            logger.error(f"Error interacting with votes: {str(e)}")
            return {'type': 'vote', 'action': 'failed', 'error': str(e)}

    def comment_on_post(self, post_id: str, comment_text: str = None) -> Dict[str, Any]:
        """Comment on a post."""
        if not self._should_take_action('comment'):
            return {'type': 'comment', 'action': 'skipped', 'reason': 'Daily limit reached'}

        try:
            # Mock comment (replace with actual Reddit API call)
            self._update_action_stats('comment')
            return {
                'type': 'comment',
                'action': 'commented',
                'post_id': post_id,
                'comment_text': comment_text or 'Great post!'
            }
        except Exception as e:
            logger.error(f"Error commenting on post: {str(e)}")
            return {'type': 'comment', 'action': 'failed', 'error': str(e)}

    def _analyze_post_context(self, submission) -> Dict[str, Any]:
        """Analyze post context for engagement."""
        try:
            return {
                'title': submission.title,
                'content': submission.selftext if hasattr(submission, 'selftext') else None,
                'score': submission.score,
                'num_comments': submission.num_comments,
                'created_utc': submission.created_utc,
                'subreddit': submission.subreddit.display_name
            }
        except Exception as e:
            logger.error(f"Error analyzing post context: {str(e)}")
            return {}

    def _generate_engaging_comment(self, post_context: Dict[str, Any]) -> str:
        """Generate an engaging comment based on post context."""
        try:
            # Use OpenAI to generate engaging comment
            response = self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful Reddit user who engages naturally with posts."},
                    {"role": "user", "content": f"Generate an engaging comment for this post:\nTitle: {post_context.get('title')}\nContent: {post_context.get('content')}"}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating engaging comment: {str(e)}")
            return "Great post! Thanks for sharing."

    def _generate_marketing_comment(self, product_info: ProductInfo, post_context: Dict[str, Any]) -> str:
        """Generate a marketing comment based on post context and product."""
        try:
            # Use OpenAI to generate marketing comment
            response = self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful Reddit user who naturally promotes products."},
                    {"role": "user", "content": f"Generate a marketing comment for this product:\nProduct: {product_info.name}\nTheme: {product_info.theme}\nPost Title: {post_context.get('title')}\nPost Content: {post_context.get('content')}"}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating marketing comment: {str(e)}")
            return "Check out this cool product!"

    def engage_with_post(self, post_id: str) -> Dict[str, Any]:
        """Engage with a post."""
        if not self._should_take_action('comment'):
            return {'type': 'engagement', 'action': 'skipped', 'reason': 'Daily limit reached'}

        try:
            # Get post context
            post = self.reddit.submission(id=post_id)
            post_context = self._analyze_post_context(post)

            # Generate and post comment
            comment = self._generate_engaging_comment(post_context)
            result = self.comment_on_post(post_id, comment)

            return {
                'type': 'engagement',
                'action': 'commented',
                'post_id': post_id,
                'comment': comment,
                'result': result
            }
        except Exception as e:
            logger.error(f"Error engaging with post: {str(e)}")
            return {'type': 'engagement', 'action': 'failed', 'error': str(e)}

    def reply_to_comment_with_marketing(self, comment_id: str, product_info: ProductInfo, post_context: Dict[str, Any]) -> Dict[str, Any]:
        """Reply to a comment with marketing content."""
        if not self._should_take_action('comment'):
            return {'type': 'marketing_reply', 'action': 'skipped', 'reason': 'Daily limit reached'}

        try:
            # Generate marketing reply
            reply = self._generate_marketing_comment(product_info, post_context)
            
            # Mock reply (replace with actual Reddit API call)
            self._update_action_stats('comment')
            
            return {
                'type': 'marketing_reply',
                'action': 'replied',
                'comment_id': comment_id,
                'reply_text': reply
            }
        except Exception as e:
            logger.error(f"Error replying to comment: {str(e)}")
            return {'type': 'marketing_reply', 'action': 'failed', 'error': str(e)}

    def engage_with_post_marketing(self, post_id: str) -> Dict[str, Any]:
        """Engage with a post using marketing content."""
        if not self._should_take_action('comment'):
            return {'type': 'marketing_engagement', 'action': 'skipped', 'reason': 'Daily limit reached'}

        try:
            # Get post context
            post = self.reddit.submission(id=post_id)
            post_context = self._analyze_post_context(post)

            # Generate marketing comment
            comment = self._generate_marketing_comment(None, post_context)
            result = self.comment_on_post(post_id, comment)

            return {
                'type': 'marketing_engagement',
                'action': 'commented',
                'post_id': post_id,
                'comment': comment,
                'result': result
            }
        except Exception as e:
            logger.error(f"Error engaging with post marketing: {str(e)}")
            return {'type': 'marketing_engagement', 'action': 'failed', 'error': str(e)}

    def interact_with_users(self, product_id: str) -> None:
        """Interact with users who engage with the product."""
        try:
            # Get product info
            product_info = self.get_product_info({'product_id': product_id})
            if not product_info:
                logger.warning(f"Product {product_id} not found")
                return

            # Get post context
            post = self.reddit.submission(id=product_info['post_id'])
            post_context = self._analyze_post_context(post)

            # Generate and post marketing comment
            comment = self._generate_marketing_comment(product_info, post_context)
            self.comment_on_post(post.id, comment)

        except Exception as e:
            logger.error(f"Error interacting with users: {str(e)}")

    async def get_product_info(self) -> List[ProductInfo]:
        """
        Get product information from Reddit content.
        
        Returns:
            List[ProductInfo]: List of product information objects
        """
        try:
            # Find a trending post and create a product
            product_info = await self.find_and_create_product()
            if product_info:
                return [product_info]
            return []
        except Exception as e:
            logger.error(f"Error getting product info: {str(e)}")
            return []

    def interact_with_subreddit(self, product_info: ProductInfo):
        """Interact with a subreddit using product information."""
        try:
            # Get subreddit
            subreddit = self.reddit.subreddit(product_info.reddit_context.subreddit)
            
            # Get trending posts
            for submission in subreddit.hot(limit=5):
                # Analyze post context
                post_context = self._analyze_post_context(submission)
                
                # Generate and post marketing comment
                comment = self._generate_marketing_comment(product_info, post_context)
                self.comment_on_post(submission.id, comment)
                
                # Take a break between actions
                time.sleep(self.personality['engagement_rules']['min_time_between_actions'])
                
        except Exception as e:
            logger.error(f"Error interacting with subreddit: {str(e)}")

    async def _find_trending_post(self, tries: int = 3, limit: int = 20):
        """Find a trending post from Reddit, retrying up to `tries` times and using up to `limit` posts per attempt."""
        logger.info(f"Starting _find_trending_post with subreddit: {self.subreddit_name}, limit: {limit}, retries: {tries}")
        try:
            for attempt in range(tries):
                # Get subreddit
                subreddit = self.reddit.subreddit(self.subreddit_name)
                found = False
                # Get trending posts
                for submission in subreddit.hot(limit=limit):
                    logger.info(f"Processing submission: {submission.title} (score: {submission.score}, is_self: {submission.is_self}, selftext length: {len(submission.selftext) if submission.selftext else 0}, age: {(datetime.now(timezone.utc) - datetime.fromtimestamp(submission.created_utc, timezone.utc)).days} days)")
                    # Skip stickied posts
                    if submission.stickied:
                        print('Skipping: stickied')
                        continue
                    # Skip posts that are too old (increased to 2 days)
                    if (datetime.now(timezone.utc) - datetime.fromtimestamp(submission.created_utc, timezone.utc)).days > 2:
                        print('Skipping: too old')
                        continue
                    # Skip posts with no content
                    if not submission.selftext:
                        print('Skipping: no selftext')
                        continue
                    # Get top comments and generate summary
                    submission.comments.replace_more(limit=0)  # Load top-level comments only
                    top_comments = submission.comments.list()[:5]  # Get top 5 comments
                    comment_texts = [comment.body for comment in top_comments if hasattr(comment, 'body')]
                    if comment_texts:
                        # Use GPT to summarize comments
                        response = self.openai.chat.completions.create(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": "Summarize the key points from these Reddit comments in 1-2 sentences."},
                                {"role": "user", "content": f"Comments:\n{chr(10).join(comment_texts)}"}
                            ]
                        )
                        comment_summary = response.choices[0].message.content.strip()
                    else:
                        comment_summary = "No comments available."
                    # Add comment summary to submission
                    submission.comment_summary = comment_summary
                    print('Returning submission:', submission.title)
                    return submission
                # If we reach here, no suitable post was found in this attempt
                logger.info(f"No suitable trending post found on attempt {attempt + 1}/{tries}")
            return None
        except Exception as e:
            logger.error(f"Error finding trending post: {str(e)}")
            print(f"Exception in _find_trending_post: {e}")
            return None 