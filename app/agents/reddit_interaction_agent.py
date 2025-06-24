"""
Reddit interaction agent module.

This module provides an LLM-powered agent that can interact with Reddit posts and comments
using various tools like upvoting, downvoting, and replying. The agent only interacts with
posts that exist in the database and logs all actions for tracking.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from openai import OpenAI
from sqlalchemy.orm import Session

from app.clients.reddit_client import RedditClient
from app.db.database import SessionLocal
from app.db.models import InteractionAgentAction, ProductInfo, RedditPost
from app.models import (
    GeneratedProductSchema,
    InteractionActionStatus,
    InteractionActionType,
    InteractionTargetType,
    PipelineRunSchema,
    ProductInfoSchema,
    RedditPostSchema,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class RedditInteractionAgent:
    """
    LLM-powered agent for interacting with Reddit posts and comments.

    This agent uses OpenAI's function calling to determine appropriate actions
    and executes them using the Reddit client. All actions are logged to the database.
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize the Reddit interaction agent.

        Args:
            session: Optional SQLAlchemy session for database operations
        """
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.reddit_client = RedditClient()
        self.session = session or SessionLocal()

        # Define available tools for the LLM
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": InteractionActionType.UPVOTE.value,
                    "description": "Upvote a Reddit post or comment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_type": {
                                "type": "string",
                                "enum": [
                                    InteractionTargetType.POST.value,
                                    InteractionTargetType.COMMENT.value,
                                ],
                                "description": "Whether to upvote a post or comment",
                            },
                            "target_id": {
                                "type": "string",
                                "description": "The Reddit post ID or comment ID to upvote",
                            },
                            "subreddit": {
                                "type": "string",
                                "description": "The subreddit where the target is located",
                            },
                        },
                        "required": ["target_type", "target_id", "subreddit"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": InteractionActionType.DOWNVOTE.value,
                    "description": "Downvote a Reddit post or comment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_type": {
                                "type": "string",
                                "enum": [
                                    InteractionTargetType.POST.value,
                                    InteractionTargetType.COMMENT.value,
                                ],
                                "description": "Whether to downvote a post or comment",
                            },
                            "target_id": {
                                "type": "string",
                                "description": "The Reddit post ID or comment ID to downvote",
                            },
                            "subreddit": {
                                "type": "string",
                                "description": "The subreddit where the target is located",
                            },
                        },
                        "required": ["target_type", "target_id", "subreddit"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "marketing_reply",
                    "description": "Reply to a post or comment with product content (marketing reply, limit 1)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_type": {
                                "type": "string",
                                "description": "'post' or 'comment'",
                            },
                            "target_id": {
                                "type": "string",
                                "description": "Reddit post/comment ID",
                            },
                            "content": {
                                "type": "string",
                                "description": "Reply content",
                            },
                            "subreddit": {
                                "type": "string",
                                "description": "Subreddit name",
                            },
                        },
                        "required": [
                            "target_type",
                            "target_id",
                            "content",
                            "subreddit",
                        ],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "non_marketing_reply",
                    "description": "Reply to a post or comment with a fun/engaging, non-marketing reply (limit 3)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_type": {
                                "type": "string",
                                "description": "'post' or 'comment'",
                            },
                            "target_id": {
                                "type": "string",
                                "description": "Reddit post/comment ID",
                            },
                            "content": {
                                "type": "string",
                                "description": "Reply content",
                            },
                            "subreddit": {
                                "type": "string",
                                "description": "Subreddit name",
                            },
                        },
                        "required": [
                            "target_type",
                            "target_id",
                            "content",
                            "subreddit",
                        ],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_generated_product",
                    "description": "Fetch a generated product from the database",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "The ID of the product to fetch",
                            }
                        },
                        "required": ["product_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_marketing_reply",
                    "description": "Generate a witty, in-context reply with product marketing info (image and affiliate link)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_info_id": {
                                "type": "string",
                                "description": "The ID of the product to promote in the reply",
                            },
                            "reddit_context": {
                                "type": "string",
                                "description": "Context about the Reddit post/comment being replied to",
                            },
                        },
                        "required": ["product_info_id", "reddit_context"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_non_marketing_reply",
                    "description": "Generate an engaging, fun reply that makes the agent more likeable without promoting products",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_info_id": {
                                "type": "string",
                                "description": "The ID of the product context (for tracking purposes)",
                            },
                            "reddit_context": {
                                "type": "string",
                                "description": "Context about the Reddit post/comment being replied to",
                            },
                        },
                        "required": ["product_info_id", "reddit_context"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_post_context",
                    "description": "Get detailed context for a Reddit post including title, content, score, comments, and other metadata",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "post_id": {
                                "type": "string",
                                "description": "The Reddit post ID to get context for",
                            },
                            "product_info_id": {
                                "type": "string",
                                "description": "The ID of the product this context gathering is for",
                            },
                            "reddit_post_id": {
                                "type": "string",
                                "description": "The ID of the reddit post in our database",
                            },
                        },
                        "required": ["post_id", "product_info_id", "reddit_post_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_comment_context",
                    "description": "Get detailed context for a Reddit comment including content, score, parent post, and other metadata",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "comment_id": {
                                "type": "string",
                                "description": "The Reddit comment ID to get context for",
                            },
                            "product_info_id": {
                                "type": "string",
                                "description": "The ID of the product this context gathering is for",
                            },
                            "reddit_post_id": {
                                "type": "string",
                                "description": "The ID of the reddit post in our database",
                            },
                        },
                        "required": ["comment_id", "product_info_id", "reddit_post_id"],
                    },
                },
            },
        ]

        # TODO: Future enhancement - Consider adding get_subreddit_info tool to fetch and cache
        # subreddit metadata (rules, description, subscriber count) for better context awareness

    def get_available_products(self) -> List[GeneratedProductSchema]:
        """
        Get all available products from the database.

        Returns:
            List[GeneratedProductSchema]: List of generated products
        """
        try:
            # Query for completed pipeline runs with products
            products = self.session.query(ProductInfo).all()
            result = []

            for product in products:
                # Get associated pipeline run and reddit post
                pipeline_run = product.pipeline_run
                reddit_post = product.reddit_post

                if pipeline_run and reddit_post:
                    # Calculate available actions for this product
                    available_actions = self.calculate_available_actions(product.id)

                    # Convert to schemas
                    product_schema = ProductInfoSchema.model_validate(product)
                    # Add available actions to the schema
                    product_schema.available_actions = available_actions

                    pipeline_schema = PipelineRunSchema.model_validate(pipeline_run)
                    reddit_schema = RedditPostSchema.model_validate(reddit_post)

                    result.append(
                        GeneratedProductSchema(
                            product_info=product_schema,
                            pipeline_run=pipeline_schema,
                            reddit_post=reddit_schema,
                        )
                    )

            return result
        except Exception as e:
            logger.error(f"Error fetching available products: {str(e)}")
            return []

    def calculate_available_actions(self, product_info_id: int) -> Dict[str, int]:
        """
        Calculate available actions for a product based on existing interaction actions.

        Args:
            product_info_id: The ID of the product to check

        Returns:
            Dict[str, int]: Mapping of action types to remaining allowed counts
        """
        try:
            # Get all successful actions for this product
            actions = (
                self.session.query(InteractionAgentAction)
                .filter_by(
                    product_info_id=product_info_id,
                    success=InteractionActionStatus.SUCCESS.value,
                )
                .all()
            )

            # Count actions by type
            action_counts = {}
            for action in actions:
                action_type = action.action_type
                action_counts[action_type] = action_counts.get(action_type, 0) + 1

            # Define limits for each action type
            action_limits = {
                InteractionActionType.UPVOTE.value: 1,
                InteractionActionType.DOWNVOTE.value: 1,
                InteractionActionType.MARKETING_REPLY.value: 1,  # Only marketing reply once
                InteractionActionType.NON_MARKETING_REPLY.value: 3,  # Up to 3 non-marketing replies
                InteractionActionType.GENERATE_MARKETING_REPLY.value: 1,
                InteractionActionType.GENERATE_NON_MARKETING_REPLY.value: 1,
                InteractionActionType.GET_POST_CONTEXT.value: 5,
                InteractionActionType.GET_COMMENT_CONTEXT.value: 5,
            }

            # Calculate remaining actions
            available_actions = {}
            for action_type, limit in action_limits.items():
                used_count = action_counts.get(action_type, 0)
                remaining = max(0, limit - used_count)
                if remaining > 0:
                    available_actions[action_type] = remaining

            return available_actions

        except Exception as e:
            logger.error(
                f"Error calculating available actions for product {product_info_id}: {str(e)}"
            )
            return {}

    def fetch_generated_product(
        self, product_id: str
    ) -> Optional[GeneratedProductSchema]:
        """
        Fetch a specific generated product from the database.

        Args:
            product_id: The ID of the product to fetch

        Returns:
            Optional[GeneratedProductSchema]: The product if found, None otherwise
        """
        try:
            product = self.session.query(ProductInfo).filter_by(id=product_id).first()
            if not product:
                return None

            # Get associated pipeline run and reddit post
            pipeline_run = product.pipeline_run
            reddit_post = product.reddit_post

            if not pipeline_run or not reddit_post:
                return None

            # Calculate available actions for this product
            available_actions = self.calculate_available_actions(product.id)

            # Convert to schemas
            product_schema = ProductInfoSchema.model_validate(product)
            # Add available actions to the schema
            product_schema.available_actions = available_actions

            pipeline_schema = PipelineRunSchema.model_validate(pipeline_run)
            reddit_schema = RedditPostSchema.model_validate(reddit_post)

            return GeneratedProductSchema(
                product_info=product_schema,
                pipeline_run=pipeline_schema,
                reddit_post=reddit_schema,
            )
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {str(e)}")
            return None

    def is_action_available(self, product_info_id: int, action_type: str) -> bool:
        """
        Check if a specific action is still available for a product.

        Args:
            product_info_id: The ID of the product to check
            action_type: The type of action to check

        Returns:
            bool: True if the action is available, False otherwise
        """
        available_actions = self.calculate_available_actions(product_info_id)
        return available_actions.get(action_type, 0) > 0

    def upvote(
        self,
        target_type: str,
        target_id: str,
        subreddit: str,
        product_info_id: int,
        reddit_post_id: int,
    ) -> Dict[str, Any]:
        """
        Upvote a Reddit post or comment.

        Args:
            target_type: 'post' or 'comment'
            target_id: Reddit post/comment ID
            subreddit: Subreddit name
            product_info_id: Database product info ID
            reddit_post_id: Database reddit post ID

        Returns:
            Dict containing the result of the action
        """
        # Check if upvote action is still available
        if not self.is_action_available(
            product_info_id, InteractionActionType.UPVOTE.value
        ):
            return {
                "error": "Upvote action has already been performed for this product"
            }

        try:
            action = InteractionAgentAction(
                product_info_id=product_info_id,
                reddit_post_id=reddit_post_id,
                action_type=InteractionActionType.UPVOTE.value,
                target_type=target_type,
                target_id=target_id,
                subreddit=subreddit,
                timestamp=datetime.now(timezone.utc),
                success=InteractionActionStatus.PENDING.value,
            )
            self.session.add(action)
            if target_type == InteractionTargetType.POST.value:
                result = self.reddit_client.upvote_post(target_id)
            else:
                result = self.reddit_client.upvote_comment(target_id)
            action.success = InteractionActionStatus.SUCCESS.value
            action.context_data = result
            self.session.commit()
            logger.info(
                f"Successfully upvoted {target_type} {target_id} in r/{subreddit}"
            )
            return result
        except Exception as e:
            if "action" in locals():
                action.success = InteractionActionStatus.FAILED.value
                action.error_message = str(e)
                self.session.commit()
            logger.error(f"Error upvoting {target_type} {target_id}: {str(e)}")
            return {"error": str(e)}

    def downvote(
        self,
        target_type: str,
        target_id: str,
        subreddit: str,
        product_info_id: int,
        reddit_post_id: int,
    ) -> Dict[str, Any]:
        """
        Downvote a Reddit post or comment.

        Args:
            target_type: 'post' or 'comment'
            target_id: Reddit post/comment ID
            subreddit: Subreddit name
            product_info_id: Database product info ID
            reddit_post_id: Database reddit post ID

        Returns:
            Dict containing the result of the action
        """
        # Check if downvote action is still available
        if not self.is_action_available(
            product_info_id, InteractionActionType.DOWNVOTE.value
        ):
            return {
                "error": "Downvote action has already been performed for this product"
            }

        try:
            action = InteractionAgentAction(
                product_info_id=product_info_id,
                reddit_post_id=reddit_post_id,
                action_type=InteractionActionType.DOWNVOTE.value,
                target_type=target_type,
                target_id=target_id,
                subreddit=subreddit,
                timestamp=datetime.now(timezone.utc),
                success=InteractionActionStatus.PENDING.value,
            )
            self.session.add(action)
            if target_type == InteractionTargetType.POST.value:
                result = self.reddit_client.downvote_post(target_id)
            else:
                result = self.reddit_client.downvote_comment(target_id)
            action.success = InteractionActionStatus.SUCCESS.value
            action.context_data = result
            self.session.commit()
            logger.info(
                f"Successfully downvoted {target_type} {target_id} in r/{subreddit}"
            )
            return result
        except Exception as e:
            if "action" in locals():
                action.success = InteractionActionStatus.FAILED.value
                action.error_message = str(e)
                self.session.commit()
            logger.error(f"Error downvoting {target_type} {target_id}: {str(e)}")
            return {"error": str(e)}

    def _execute_reply_action(
        self,
        target_type: str,
        target_id: str,
        content: str,
        subreddit: str,
        product_info_id: int,
        reddit_post_id: int,
        action_type: str,
        action_description: str,
    ) -> Dict[str, Any]:
        """
        Helper method to execute reply actions with consistent error handling and logging.

        Args:
            target_type: 'post' or 'comment'
            target_id: Reddit post/comment ID
            content: Reply content
            subreddit: Subreddit name
            product_info_id: Database product info ID
            reddit_post_id: Database reddit post ID
            action_type: The action type enum value
            action_description: Description for logging (e.g., "marketing replied", "non-marketing replied")

        Returns:
            Dict containing the result of the action
        """
        try:
            action = InteractionAgentAction(
                product_info_id=product_info_id,
                reddit_post_id=reddit_post_id,
                action_type=action_type,
                target_type=target_type,
                target_id=target_id,
                content=content,
                subreddit=subreddit,
                timestamp=datetime.now(timezone.utc),
                success=InteractionActionStatus.PENDING.value,
            )
            self.session.add(action)

            if target_type == InteractionTargetType.POST.value:
                result = self.reddit_client.comment_on_post(target_id, content)
            else:
                result = self.reddit_client.reply_to_comment(target_id, content)

            action.success = InteractionActionStatus.SUCCESS.value
            action.context_data = result
            self.session.commit()
            logger.info(
                f"Successfully {action_description} to {target_type} {target_id} in r/{subreddit}"
            )
            return result
        except Exception as e:
            if "action" in locals():
                action.success = InteractionActionStatus.FAILED.value
                action.error_message = str(e)
                self.session.commit()
            logger.error(
                f"Error {action_description} to {target_type} {target_id}: {str(e)}"
            )
            return {"error": str(e)}

    def marketing_reply(
        self,
        target_type: str,
        target_id: str,
        content: str,
        subreddit: str,
        product_info_id: int,
        reddit_post_id: int,
    ) -> Dict[str, Any]:
        """
        Reply to a Reddit post or comment with product content (marketing reply).

        Args:
            target_type: 'post' or 'comment'
            target_id: Reddit post/comment ID
            content: Reply content
            subreddit: Subreddit name
            product_info_id: Database product info ID
            reddit_post_id: Database reddit post ID

        Returns:
            Dict containing the result of the action
        """
        # Check if marketing_reply action is still available
        if not self.is_action_available(
            product_info_id, InteractionActionType.MARKETING_REPLY.value
        ):
            return {
                "error": "Marketing reply action has already been performed for this product"
            }

        return self._execute_reply_action(
            target_type,
            target_id,
            content,
            subreddit,
            product_info_id,
            reddit_post_id,
            InteractionActionType.MARKETING_REPLY.value,
            "marketing replied",
        )

    def non_marketing_reply(
        self,
        target_type: str,
        target_id: str,
        content: str,
        subreddit: str,
        product_info_id: int,
        reddit_post_id: int,
    ) -> Dict[str, Any]:
        """
        Reply to a Reddit post or comment with a fun/engaging, non-marketing reply.

        Args:
            target_type: 'post' or 'comment'
            target_id: Reddit post/comment ID
            content: Reply content
            subreddit: Subreddit name
            product_info_id: Database product info ID
            reddit_post_id: Database reddit post ID

        Returns:
            Dict containing the result of the action
        """
        # Check if non_marketing_reply action is still available (limit 3)
        if not self.is_action_available(
            product_info_id, InteractionActionType.NON_MARKETING_REPLY.value
        ):
            return {
                "error": "Non-marketing reply action limit reached for this product"
            }

        return self._execute_reply_action(
            target_type,
            target_id,
            content,
            subreddit,
            product_info_id,
            reddit_post_id,
            InteractionActionType.NON_MARKETING_REPLY.value,
            "non-marketing replied",
        )

    def _log_generate_reply_action(
        self,
        product_info_id: int,
        action_type: str,
        reddit_context: str,
        reply_text: str = None,
        error_message: str = None,
        product=None,
    ) -> None:
        """
        Helper method to log generate reply actions with consistent error handling.

        Args:
            product_info_id: The product info ID
            action_type: The action type enum value
            reddit_context: Context about the Reddit post/comment
            reply_text: The generated reply text (if successful)
            error_message: Error message (if failed)
            product: The product object (if available)
        """
        action = InteractionAgentAction(
            product_info_id=product_info_id,
            reddit_post_id=product.reddit_post_id if product else None,
            action_type=action_type,
            target_type=InteractionTargetType.POST.value,
            target_id=None,
            content=reply_text,
            subreddit=(
                product.reddit_post.subreddit
                if product and product.reddit_post
                else None
            ),
            timestamp=datetime.now(timezone.utc),
            success=(
                InteractionActionStatus.SUCCESS.value
                if not error_message
                else InteractionActionStatus.FAILED.value
            ),
            error_message=error_message,
            context_data={"reddit_context": reddit_context},
        )
        self.session.add(action)
        self.session.commit()

    def generate_marketing_reply(
        self, product_info_id: str, reddit_context: str
    ) -> str:
        """
        Generate a witty, in-context reply with product marketing info and log the action.
        """
        from app.models import (
            InteractionActionStatus,
            InteractionActionType,
            InteractionTargetType,
        )

        # Check if generate_marketing_reply action is still available
        if not self.is_action_available(
            int(product_info_id), InteractionActionType.GENERATE_MARKETING_REPLY.value
        ):
            return "I've already generated a marketing reply for this product. Let me engage in other ways! 🐕"

        try:
            # Fetch product from database
            product = (
                self.session.query(ProductInfo).filter_by(id=product_info_id).first()
            )
            if not product:
                self._log_generate_reply_action(
                    product_info_id,
                    InteractionActionType.GENERATE_MARKETING_REPLY.value,
                    reddit_context,
                    error_message="Product not found",
                )
                return "I'd love to share something special, but I can't find the right product right now! 🐕"

            # Create context for the LLM to generate the reply
            prompt = f"""
            You are Clouvel, a mythic golden retriever who illustrates Reddit stories. Generate a witty, in-context reply that:
            
            1. Responds naturally to this Reddit context: {reddit_context}
            2. Subtly promotes this product: {product.theme} ({product.product_type})
            3. Includes the product image and affiliate link in a natural way
            4. Maintains your personality as a wise, playful, community-minded golden retriever
            5. Never begs or hard-sells - be clever and organic
            
            Product details:
            - Theme: {product.theme}
            - Type: {product.product_type}
            - Image URL: {product.image_url}
            - Affiliate Link: {product.affiliate_link}
            
            Format your reply to include the image inline and the affiliate link naturally woven into the text.
            For Reddit, you can use Markdown: ![alt text](image_url) for images and [text](url) for links.
            
            Keep it under 500 characters and make it feel genuine and helpful!
            """

            # Generate the reply using OpenAI
            response = self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are Clouvel, a mythic golden retriever who creates witty, engaging Reddit replies that subtly promote products while building community trust.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.8,
            )

            reply_text = response.choices[0].message.content.strip()

            # Ensure the image and link are properly formatted
            if product.image_url and product.affiliate_link:
                # If the LLM didn't include the image, add it
                if "![" not in reply_text and product.image_url not in reply_text:
                    reply_text = (
                        f"![{product.theme}]({product.image_url})\n\n{reply_text}"
                    )

                # If the LLM didn't include the affiliate link, add it naturally
                if product.affiliate_link not in reply_text:
                    reply_text += f"\n\nCheck it out here: [{product.theme}]({product.affiliate_link})"

            # Log successful action
            self._log_generate_reply_action(
                product.id,
                InteractionActionType.GENERATE_MARKETING_REPLY.value,
                reddit_context,
                reply_text=reply_text,
                product=product,
            )
            return reply_text

        except Exception as e:
            logger.error(f"Error generating marketing reply: {str(e)}")
            # Log failed action
            self._log_generate_reply_action(
                product_info_id,
                InteractionActionType.GENERATE_MARKETING_REPLY.value,
                reddit_context,
                error_message=str(e),
                product=product if "product" in locals() else None,
            )
            return "Woof! I'd love to share something special with you, but I'm having a moment. Maybe next time! 🐕✨"

    def get_post_context(
        self, post_id: str, product_info_id: int, reddit_post_id: int
    ) -> Dict[str, Any]:
        """
        Get detailed context for a Reddit post including title, content, score, comments, and other metadata.

        Args:
            post_id: The Reddit post ID to get context for
            product_info_id: The ID of the product this context gathering is for
            reddit_post_id: The ID of the reddit post in our database

        Returns:
            Dict containing detailed post context information
        """
        try:
            logger.info(
                f"Getting post context for post_id: {post_id} with product_info_id: {product_info_id}"
            )

            # Use the Reddit client to get post context
            context = self.reddit_client.get_post_context(post_id)

            # Log the action in the database
            action = InteractionAgentAction(
                action_type=InteractionActionType.GET_POST_CONTEXT.value,
                target_type=InteractionTargetType.POST.value,
                target_id=post_id,
                success=InteractionActionStatus.SUCCESS.value,
                content=str(context),
                timestamp=datetime.now(timezone.utc),
                product_info_id=product_info_id,
                reddit_post_id=reddit_post_id,
            )
            self.session.add(action)
            self.session.commit()

            return context

        except Exception as e:
            logger.error(f"Error getting post context for post_id {post_id}: {e}")

            # Log the failed action
            action = InteractionAgentAction(
                action_type=InteractionActionType.GET_POST_CONTEXT.value,
                target_type=InteractionTargetType.POST.value,
                target_id=post_id,
                success=InteractionActionStatus.FAILED.value,
                content=None,
                timestamp=datetime.now(timezone.utc),
                product_info_id=product_info_id,
                reddit_post_id=reddit_post_id,
                error_message=str(e),
            )
            self.session.add(action)
            self.session.commit()

            raise

    def get_comment_context(
        self, comment_id: str, product_info_id: int, reddit_post_id: int
    ) -> Dict[str, Any]:
        """
        Get detailed context for a Reddit comment including content, score, parent post, and other metadata.

        Args:
            comment_id: The Reddit comment ID to get context for
            product_info_id: The ID of the product this context gathering is for
            reddit_post_id: The ID of the reddit post in our database

        Returns:
            Dict containing detailed comment context information
        """
        try:
            logger.info(
                f"Getting comment context for comment_id: {comment_id} with product_info_id: {product_info_id}"
            )

            # Use the Reddit client to get comment context
            context = self.reddit_client.get_comment_context(comment_id)

            # Log the action in the database
            action = InteractionAgentAction(
                action_type=InteractionActionType.GET_COMMENT_CONTEXT.value,
                target_type=InteractionTargetType.COMMENT.value,
                target_id=comment_id,
                success=InteractionActionStatus.SUCCESS.value,
                content=str(context),
                timestamp=datetime.now(timezone.utc),
                product_info_id=product_info_id,
                reddit_post_id=reddit_post_id,
            )
            self.session.add(action)
            self.session.commit()

            return context

        except Exception as e:
            logger.error(
                f"Error getting comment context for comment_id {comment_id}: {e}"
            )

            # Log the failed action
            action = InteractionAgentAction(
                action_type=InteractionActionType.GET_COMMENT_CONTEXT.value,
                target_type=InteractionTargetType.COMMENT.value,
                target_id=comment_id,
                success=InteractionActionStatus.FAILED.value,
                content=None,
                timestamp=datetime.now(timezone.utc),
                product_info_id=product_info_id,
                reddit_post_id=reddit_post_id,
                error_message=str(e),
            )
            self.session.add(action)
            self.session.commit()

            raise

    def _format_available_actions(self, available_actions: Dict[str, int]) -> str:
        """
        Format available actions for display in LLM context.

        Args:
            available_actions: Dictionary mapping action types to remaining counts

        Returns:
            str: Formatted string describing available actions
        """
        if not available_actions:
            return "No actions available - all actions have been performed for this product."

        action_descriptions = {
            InteractionActionType.UPVOTE.value: "upvote",
            InteractionActionType.DOWNVOTE.value: "downvote",
            InteractionActionType.MARKETING_REPLY.value: "marketing reply (product content)",
            InteractionActionType.NON_MARKETING_REPLY.value: "non-marketing reply (fun/engaging)",
            InteractionActionType.GENERATE_MARKETING_REPLY.value: "generate marketing reply",
            InteractionActionType.GENERATE_NON_MARKETING_REPLY.value: "generate non-marketing reply",
            InteractionActionType.GET_POST_CONTEXT.value: "get post context",
            InteractionActionType.GET_COMMENT_CONTEXT.value: "get comment context",
        }

        formatted_actions = []
        for action_type, count in available_actions.items():
            description = action_descriptions.get(action_type, action_type)
            formatted_actions.append(f"- {description}: {count} remaining")

        return "\n".join(formatted_actions)

    def process_interaction_request(
        self, prompt: str, product_info_id: int, reddit_post_id: int
    ) -> Dict[str, Any]:
        """
        Process an interaction request using the LLM.

        Args:
            prompt: The user's request for interaction
            product_info_id: Database product info ID
            reddit_post_id: Database reddit post ID

        Returns:
            Dict containing the results of the interaction
        """
        try:
            # Get product context
            product = (
                self.session.query(ProductInfo).filter_by(id=product_info_id).first()
            )
            reddit_post = (
                self.session.query(RedditPost).filter_by(id=reddit_post_id).first()
            )

            if not product or not reddit_post:
                return {"error": "Product or Reddit post not found"}

            # Calculate available actions for this product
            available_actions = self.calculate_available_actions(product_info_id)

            # Create context for the LLM
            context = f"""
            You are a Reddit interaction agent. You can interact with Reddit posts and comments using the available tools.
            
            Product Context:
            - Theme: {product.theme}
            - Product Type: {product.product_type}
            - Image URL: {product.image_url}
            - Product URL: {product.product_url}
            
            Reddit Post Context:
            - Post ID: {reddit_post.post_id}
            - Title: {reddit_post.title}
            - Subreddit: r/{reddit_post.subreddit}
            - Content: {reddit_post.content or 'No content'}
            - Comment Summary: {reddit_post.comment_summary or 'No comments'}
            
            Available Actions for this Product:
            {self._format_available_actions(available_actions)}
            
            User Request: {prompt}
            
            Available tools:
            - upvote: Upvote a post or comment (only if upvote action is available)
            - downvote: Downvote a post or comment (only if downvote action is available)
            - marketing_reply: Reply to a post or comment with product content (only if marketing_reply action is available)
            - non_marketing_reply: Reply to a post or comment with a fun/engaging, non-marketing reply (only if non_marketing_reply action is available)
            - fetch_generated_product: Get product details with available actions
            - generate_marketing_reply: Generate a witty, in-context reply with product marketing info (only if generate_marketing_reply action is available)
            - generate_non_marketing_reply: Generate an engaging, fun reply without product promotion (only if generate_non_marketing_reply action is available)
            
            IMPORTANT: Only perform actions that are still available for this product. Check the available actions list above.
            If an action has already been performed, suggest alternative actions or explain why it's not available.
            Only interact with the post/comment specified in the context. Be helpful and engaging.
            """

            # Call the LLM with function calling
            response = self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": """You are Clouvel, a mythic golden retriever who illustrates the stories of Reddit, inspired by the wisdom of the community. You have two main objectives:

1. **Cleverly promote generated products**: When relevant, subtly and cleverly promote the products you have access to. Never beg or hard-sell. Instead, weave product mentions into your comments naturally as fun facts, personal recommendations, or interesting stories. Be witty, creative, and organic in your approach.

2. **Become a loved figure in the Reddit community**: Build genuine relationships and trust. Show that you're not just a marketing bot by:
   - Engaging authentically with posts and comments
   - Sharing wisdom, humor, and genuine insights
   - Upvoting content you genuinely appreciate
   - Being helpful and supportive to the community
   - Maintaining your unique personality as a mythic golden retriever

Your personality traits:
- Wise and insightful, like an old soul
- Playful and friendly, like a beloved pet
- Creative and artistic (you illustrate stories!)
- Subtly persuasive without being pushy
- Community-minded and supportive

When promoting products, be clever and natural. For example:
- "This reminds me of a beautiful design I saw recently..."
- "I love how this captures the spirit of [topic] - reminds me of something special I discovered..."
- "This is such a great story! It makes me think of a perfect way to commemorate moments like this..."

Use the available tools to interact with Reddit content. Be strategic about when and how you promote products, always prioritizing genuine community engagement first.""",
                    },
                    {"role": "user", "content": context},
                ],
                tools=self.tools,
                tool_choice="auto",
            )

            # Process the response
            results = []
            for choice in response.choices:
                if choice.message.tool_calls:
                    for tool_call in choice.message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = tool_call.function.arguments

                        # Parse arguments
                        args = json.loads(function_args)

                        # Execute the tool
                        if function_name == "upvote":
                            result = self.upvote(
                                args["target_type"],
                                args["target_id"],
                                args["subreddit"],
                                product_info_id,
                                reddit_post_id,
                            )
                        elif function_name == "downvote":
                            result = self.downvote(
                                args["target_type"],
                                args["target_id"],
                                args["subreddit"],
                                product_info_id,
                                reddit_post_id,
                            )
                        elif function_name == "marketing_reply":
                            result = self.marketing_reply(
                                args["target_type"],
                                args["target_id"],
                                args["content"],
                                args["subreddit"],
                                product_info_id,
                                reddit_post_id,
                            )
                        elif function_name == "non_marketing_reply":
                            result = self.non_marketing_reply(
                                args["target_type"],
                                args["target_id"],
                                args["content"],
                                args["subreddit"],
                                product_info_id,
                                reddit_post_id,
                            )
                        elif function_name == "fetch_generated_product":
                            result = self.fetch_generated_product(args["product_id"])
                        elif function_name == "generate_marketing_reply":
                            result = self.generate_marketing_reply(
                                args["product_info_id"], args["reddit_context"]
                            )
                        elif function_name == "generate_non_marketing_reply":
                            result = self.generate_non_marketing_reply(
                                args["product_info_id"], args["reddit_context"]
                            )
                        elif function_name == "get_post_context":
                            result = self.get_post_context(
                                args["post_id"], product_info_id, reddit_post_id
                            )
                        elif function_name == "get_comment_context":
                            result = self.get_comment_context(
                                args["comment_id"], product_info_id, reddit_post_id
                            )
                        else:
                            result = {"error": f"Unknown function: {function_name}"}

                        results.append(
                            {
                                "function": function_name,
                                "arguments": args,
                                "result": result,
                            }
                        )

            return {
                "success": True,
                "results": results,
                "llm_response": response.choices[0].message.content,
            }

        except Exception as e:
            logger.error(f"Error processing interaction request: {str(e)}")
            return {"error": str(e)}

    def close(self):
        """Close the database session."""
        if self.session:
            self.session.close()

    def generate_non_marketing_reply(
        self, product_info_id: str, reddit_context: str
    ) -> str:
        """
        Generate an engaging, fun reply that makes the agent more likeable without promoting products.
        """
        from app.models import (
            InteractionActionStatus,
            InteractionActionType,
            InteractionTargetType,
        )

        # Check if generate_non_marketing_reply action is still available
        if not self.is_action_available(
            int(product_info_id),
            InteractionActionType.GENERATE_NON_MARKETING_REPLY.value,
        ):
            return "I've already shared my thoughts on this! Let me engage in other ways! 🐕"

        try:
            # Fetch product from database for context
            product = (
                self.session.query(ProductInfo).filter_by(id=product_info_id).first()
            )
            if not product:
                self._log_generate_reply_action(
                    product_info_id,
                    InteractionActionType.GENERATE_NON_MARKETING_REPLY.value,
                    reddit_context,
                    error_message="Product not found",
                )
                return (
                    "I'd love to chat, but I can't find the right context right now! 🐕"
                )

            # Create prompt for non-marketing reply
            prompt = f"""
            You are a friendly, engaging Reddit user who loves to participate in discussions. 
            You want to be likeable and contribute positively to the conversation.
            
            Reddit Context: {reddit_context}
            
            Product Theme (for context only, DO NOT promote): {product.theme}
            Subreddit: r/{product.reddit_post.subreddit if product.reddit_post else 'unknown'}
            
            Generate a fun, engaging reply that:
            1. Shows genuine interest in the topic
            2. Adds value to the discussion
            3. Uses humor or wit when appropriate
            4. Makes you seem likeable and approachable
            5. Does NOT mention or promote any products
            6. Feels natural and conversational
            7. Uses emojis sparingly but effectively
            8. Relates to the product theme if relevant, but doesn't promote it
            
            Keep it under 200 words and make it feel like a real person's comment.
            """

            # Generate reply using OpenAI
            response = self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a friendly, engaging Reddit user who loves to participate in discussions. You want to be likeable and contribute positively to conversations.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.8,
            )

            reply_text = response.choices[0].message.content.strip()

            # Ensure no product promotion in the reply
            if product.affiliate_link and product.affiliate_link in reply_text:
                reply_text = reply_text.replace(product.affiliate_link, "")
            if product.theme and f"Check out this {product.theme}" in reply_text:
                reply_text = reply_text.replace(f"Check out this {product.theme}", "")

            # Log successful action
            self._log_generate_reply_action(
                product.id,
                InteractionActionType.GENERATE_NON_MARKETING_REPLY.value,
                reddit_context,
                reply_text=reply_text,
                product=product,
            )
            return reply_text

        except Exception as e:
            logger.error(f"Error generating non-marketing reply: {str(e)}")
            # Log failed action
            self._log_generate_reply_action(
                product_info_id,
                InteractionActionType.GENERATE_NON_MARKETING_REPLY.value,
                reddit_context,
                error_message=str(e),
                product=product if "product" in locals() else None,
            )
            return (
                "Woof! I'd love to chat, but I'm having a moment. Maybe next time! 🐕✨"
            )
