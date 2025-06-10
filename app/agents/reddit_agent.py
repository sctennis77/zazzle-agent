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
import openai
import json
from app.image_generator import ImageGenerator

logger = logging.getLogger(__name__)

class RedditAgent(ChannelAgent):
    """Reddit agent that behaves like a user to distribute content effectively."""

    def __init__(self, personality: Optional[Dict[str, Any]] = None, subreddit_name: str = None, model: str = "dall-e-2"):
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
        
        # Initialize OpenAI client
        self.openai_client = openai.OpenAI()
        
        # Initialize ImageGenerator with specified model
        self.image_generator = ImageGenerator(model=model)
        
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

    def interact_with_votes(self, post_id: str, comment_id: str = None) -> None:
        """Interact with a post or comment by upvoting and downvoting."""
        try:
            if comment_id:
                # Handle comment voting
                comment = self.reddit.comment(id=comment_id)
                comment.upvote()
                logger.info(f"Upvoted comment {comment_id} in post {post_id}")
                comment.downvote()
                logger.info(f"Downvoted comment {comment_id} in post {post_id}")
                return {
                    'type': 'comment',
                    'post_id': post_id,
                    'comment_id': comment_id,
                    'comment_text': comment.body,
                    'comment_link': f"https://reddit.com/r/{comment.subreddit.display_name}/comments/{post_id}/_/{comment_id}"
                }
            else:
                # Handle post voting
                submission = self.reddit.submission(id=post_id)
                submission.upvote()
                logger.info(f"Upvoted post {post_id}")
                submission.downvote()
                logger.info(f"Downvoted post {post_id}")
                return {
                    'type': 'post',
                    'post_id': post_id,
                    'post_title': submission.title,
                    'post_link': f"https://reddit.com/r/{submission.subreddit.display_name}/comments/{post_id}"
                }
        except Exception as e:
            logger.error(f"Error interacting with votes for {'comment' if comment_id else 'post'} {comment_id or post_id}: {str(e)}")
            return None

    def comment_on_post(self, post_id: str, comment_text: str = None) -> Dict[str, Any]:
        """Comment on a post with the given text."""
        try:
            submission = self.reddit.submission(id=post_id)
            
            # Generate a comment if none provided
            if not comment_text:
                comment_text = "Thanks for sharing this interesting post! I appreciate the insights."
            
            # In test mode, just return the action details without posting
            return {
                'type': 'post_comment',
                'post_id': post_id,
                'post_title': submission.title,
                'post_link': f"https://reddit.com/r/{submission.subreddit.display_name}/comments/{post_id}",
                'comment_text': comment_text,
                'action': 'Would reply to post with comment'
            }
            
        except Exception as e:
            logger.error(f"Error commenting on post {post_id}: {str(e)}")
            return None

    def _analyze_post_context(self, submission) -> Dict[str, Any]:
        """Analyze a post and its comments to understand the context."""
        try:
            # Get post details
            post_context = {
                'title': submission.title,
                'text': submission.selftext,
                'score': submission.score,
                'num_comments': submission.num_comments,
                'created_utc': submission.created_utc,
                'top_comments': []
            }
            
            # Get top-level comments
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list()[:5]:  # Get top 5 comments
                if not comment.stickied:
                    post_context['top_comments'].append({
                        'text': comment.body,
                        'score': comment.score,
                        'author': str(comment.author),
                        'created_utc': comment.created_utc
                    })
            
            return post_context
        except Exception as e:
            logger.error(f"Error analyzing post context: {str(e)}")
            return None

    def _generate_engaging_comment(self, post_context: Dict[str, Any]) -> str:
        """Generate an engaging comment based on post context."""
        try:
            # Prepare the prompt for OpenAI
            prompt = f"""Based on this Reddit post and its comments, generate a short, engaging response that:
1. Shows understanding of the topic
2. Adds value to the discussion
3. Maintains a friendly, conversational tone
4. Is concise (2-3 sentences max)

Post Title: {post_context['title']}
Post Content: {post_context['text']}

Top Comments:
{chr(10).join([f"- {c['text']} (by u/{c['author']})" for c in post_context['top_comments']])}

Generate a natural, engaging response:"""

            # Use OpenAI to generate the comment
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful Reddit user who engages in meaningful discussions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating engaging comment: {str(e)}")
            return "Thanks for sharing this interesting post! I appreciate the insights."

    def _generate_marketing_comment(self, product: Product, post_context: Dict[str, Any]) -> str:
        """Generate a marketing comment based on product info and post context."""
        try:
            product_description = product.content if product.content else f"{product.name} available on Zazzle."
            affiliate_link = product.affiliate_link if product.affiliate_link else "#"

            prompt = f"""Based on the following Reddit post and its comments, craft a concise marketing comment (2-4 sentences) for a Zazzle product:

Post Title: {post_context['title']}
Post Content: {post_context['text']}
Top Comments:
{chr(10).join([f"- {c['text']} (by u/{c['author']})" for c in post_context['top_comments']])}

Product Name: {product.name}
Product Description: {product_description}
Affiliate Link: {affiliate_link}

Key considerations for the comment:
- Naturally integrate the product.
- Maintain a friendly, non-spammy tone.
- Encourage engagement.
- Include the affiliate link at the end (e.g., 'Check it out here: [Link]').

Marketing Comment:"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful Reddit user who occasionally shares relevant product recommendations naturally."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating marketing comment: {str(e)}")
            return f"Check out this cool product: {product.name} - {affiliate_link}"

    def engage_with_post(self, post_id: str) -> Dict[str, Any]:
        """Engage with a post by analyzing context and generating an engaging comment."""
        try:
            submission = self.reddit.submission(id=post_id)
            
            # Analyze post context
            post_context = self._analyze_post_context(submission)
            if not post_context:
                return None
            
            # Generate engaging comment
            comment_text = self._generate_engaging_comment(post_context)
            
            # In test mode, return the action details without posting
            return {
                'type': 'post_engagement',
                'post_id': post_id,
                'post_title': submission.title,
                'post_link': f"https://reddit.com/r/{submission.subreddit.display_name}/comments/{post_id}",
                'post_context': post_context,
                'comment_text': comment_text,
                'action': 'Would engage with post using generated comment'
            }
            
        except Exception as e:
            logger.error(f"Error engaging with post {post_id}: {str(e)}")
            return None

    def reply_to_comment_with_marketing(self, comment_id: str, product: Product, post_context: Dict[str, Any]) -> Dict[str, Any]:
        """Reply to a comment with a marketing comment that includes product information."""
        try:
            comment = self.reddit.comment(id=comment_id)
            
            # Generate marketing comment
            marketing_comment_text = self._generate_marketing_comment(product, post_context)
            
            # In test mode, just return the action details without posting
            return {
                'type': 'comment_marketing_reply',
                'comment_id': comment_id,
                'comment_text': comment.body,
                'post_id': comment.submission.id,
                'post_title': comment.submission.title,
                'post_link': f"https://reddit.com/r/{comment.subreddit.display_name}/comments/{comment.submission.id}/_/{comment.id}",
                'product_info': {
                    'name': product.name,
                    'affiliate_link': product.affiliate_link
                },
                'reply_text': marketing_comment_text,
                'action': 'Would reply to comment with marketing content'
            }
            
        except Exception as e:
            logger.error(f"Error replying to comment {comment_id} with marketing content: {str(e)}")
            return None

    def engage_with_post_marketing(self, post_id: str) -> Dict[str, Any]:
        """Engage with a post by analyzing context and generating a marketing comment."""
        try:
            submission = self.reddit.submission(id=post_id)
            
            # Analyze post context
            post_context = self._analyze_post_context(submission)
            if not post_context:
                return None
            
            # Determine product idea based on post content and comments
            product_info = self._determine_product_idea(
                post_title=submission.title,
                post_content=submission.selftext,
                comments=post_context['top_comments']
            )
            
            if not product_info:
                logger.warning(f"No suitable product idea found for post {post_id}.")
                return None
            
            # Ensure required fields for product designer
            product_info.setdefault('image_url', 'https://via.placeholder.com/150')
            product_info.setdefault('image_iid', 'test_image_iid')
            # Create product using product designer
            product_info = self.product_designer.create_product(product_info)
            
            # In test mode, return the action details without posting
            return {
                'type': 'post_marketing_comment',
                'post_id': post_id,
                'post_title': submission.title,
                'post_link': f"https://reddit.com/r/{submission.subreddit.display_name}/comments/{post_id}",
                'post_context': post_context,
                'product_info': product_info,
                'comment_text': product_info.get('description', "Check out this cool product!"),
                'action': 'Would reply to post with marketing comment'
            }
            
        except Exception as e:
            logger.error(f"Error engaging with post {post_id} for marketing: {str(e)}")
            return None

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
                
                # Get top-level comments
                trending_post.comments.replace_more(limit=0)  # Load top-level comments only
                for comment in trending_post.comments.list():
                    if not comment.stickied:  # Skip stickied comments
                        result = self.interact_with_votes(post_id, comment.id)
                        if result:
                            logger.info(f"Interaction result: {result}")
                        break  # Process only one comment for testing
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
        Analyze Reddit content using an LLM to determine product ideas and design instructions.
        
        Args:
            post_title: The title of the Reddit post
            post_content: The content/body of the Reddit post
            comments: List of top comments with their content
            
        Returns:
            Dict containing product idea details (text, image_description, theme, color, quantity)
            or None if no suitable idea is found.
        """
        try:
            combined_content = f"Title: {post_title}\n"
            if post_content: 
                combined_content += f"Content: {post_content}\n"
            if comments:
                combined_content += "Comments:\n"
                for i, comment in enumerate(comments[:5]): # Use top 5 comments
                    combined_content += f"- {comment.get('body', '')}\n"

            system_prompt = """You are a creative assistant that specializes in generating unique product ideas for Zazzle, specifically customizable stickers. 
            Based on Reddit post and comment content, identify a fun, witty, or relevant concept for a sticker. 
            Provide design instructions including text for the sticker, a description for an image to go on the sticker, a theme, and suggested color and quantity.
            If you cannot find a suitable idea, respond with an empty JSON object. Make sure the 'text' is concise and punchy, it has to fit into a 1.5 inch round sticker.
            The image_description should be detailed enough for an image generation model.
            Output your response as a JSON object with the following keys: 'text', 'image_description', 'theme', 'color', 'quantity'.
            Example: {'text': 'Fore Moon', 'image_description': 'A golfball soaring to space on a starry evening in impressionist style', 'theme': 'golf joke', 'color': 'Blue', 'quantity': 1}
            """

            user_prompt = f"Analyze the following Reddit content for product ideas:\n\n{combined_content}"

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini", # Using a cost-effective model for this task
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=200
            )

            product_idea_json = json.loads(response.choices[0].message.content)

            # Validate and return the extracted product idea
            if not all(k in product_idea_json for k in ['text', 'image_description', 'theme']):
                logger.warning("LLM did not return all required product idea fields.")
                return None
            
            # Add default color and quantity if not provided by LLM
            product_idea_json.setdefault('color', 'Blue')
            product_idea_json.setdefault('quantity', 1)

            return product_idea_json

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from LLM response: {e}")
            logger.error(f"LLM raw response: {response.choices[0].message.content}")
            return None
        except Exception as e:
            logger.error(f"Error determining product idea with LLM: {str(e)}")
            return None

    async def find_and_create_product(self) -> Optional[Dict]:
        """Find a suitable post and create a product based on it."""
        try:
            # Get a trending post from r/golf
            subreddit = self.reddit.subreddit("golf")
            trending_post = next(subreddit.hot(limit=1), None)
            
            if not trending_post:
                logger.warning("No trending post found in r/golf")
                return None
            
            # Analyze post context
            post_context = self._analyze_post_context(trending_post)
            
            # Determine product idea from post using LLM
            product_idea = self._determine_product_idea(
                post_title=post_context['title'],
                post_content=post_context.get('text'),
                comments=post_context.get('top_comments', [])
            )
            
            if not product_idea:
                logger.warning("Could not determine product idea from post")
                return None
            
            # Generate image using the image_description from the product idea
            image_description = product_idea.get('image_description')
            if image_description:
                try:
                    # Pass the product's template ID for naming the generated image
                    template_id = self.product_designer.template.zazzle_template_id if self.product_designer.template else None
                    imgur_url, local_path = await self.image_generator.generate_image(image_description, template_id=template_id)
                    product_idea['image'] = imgur_url  # Update image URL with generated Imgur URL
                    product_idea['image_local_path'] = local_path # Store local path
                except Exception as e:
                    logger.error(f"Failed to generate image for product idea: {str(e)}")
                    # Fallback to placeholder if image generation fails
                    product_idea.setdefault('image', 'https://via.placeholder.com/150')
                    product_idea.setdefault('image_local_path', None)
            else:
                # Add placeholders for image_url and image_iid if no image_description
                product_idea.setdefault('image', 'https://via.placeholder.com/150')
                product_idea.setdefault('image_local_path', None)

            # Create product using product designer
            product_info = self.product_designer.create_product(product_idea)
            
            if not product_info:
                logger.warning("Failed to create product")
                return None
            
            # Add Reddit context to product info
            product_info['reddit_context'] = {
                'id': trending_post.id,
                'title': trending_post.title,
                'url': f"https://reddit.com{trending_post.permalink}",
                'theme': product_idea.get('theme', 'default')  # Include theme from product_idea
            }
            
            return product_info
            
        except Exception as e:
            logger.error(f"Error in find_and_create_product: {str(e)}")
            return None 