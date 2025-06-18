"""
Reddit interaction agent module.

This module provides an LLM-powered agent that can interact with Reddit posts and comments
using various tools like upvoting, downvoting, and replying. The agent only interacts with
posts that exist in the database and logs all actions for tracking.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from openai import OpenAI
from sqlalchemy.orm import Session
from app.clients.reddit_client import RedditClient
from app.db.models import ProductInfo, RedditPost, InteractionAgentAction
from app.models import GeneratedProductSchema, ProductInfoSchema, PipelineRunSchema, RedditPostSchema
from app.utils.logging_config import get_logger
from app.db.database import SessionLocal

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
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.reddit_client = RedditClient()
        self.session = session or SessionLocal()
        
        # Define available tools for the LLM
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "upvote",
                    "description": "Upvote a Reddit post or comment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_type": {
                                "type": "string",
                                "enum": ["post", "comment"],
                                "description": "Whether to upvote a post or comment"
                            },
                            "target_id": {
                                "type": "string",
                                "description": "The Reddit post ID or comment ID to upvote"
                            },
                            "subreddit": {
                                "type": "string",
                                "description": "The subreddit where the target is located"
                            }
                        },
                        "required": ["target_type", "target_id", "subreddit"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "downvote",
                    "description": "Downvote a Reddit post or comment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_type": {
                                "type": "string",
                                "enum": ["post", "comment"],
                                "description": "Whether to downvote a post or comment"
                            },
                            "target_id": {
                                "type": "string",
                                "description": "The Reddit post ID or comment ID to downvote"
                            },
                            "subreddit": {
                                "type": "string",
                                "description": "The subreddit where the target is located"
                            }
                        },
                        "required": ["target_type", "target_id", "subreddit"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "reply",
                    "description": "Reply to a Reddit post or comment",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_type": {
                                "type": "string",
                                "enum": ["post", "comment"],
                                "description": "Whether to reply to a post or comment"
                            },
                            "target_id": {
                                "type": "string",
                                "description": "The Reddit post ID or comment ID to reply to"
                            },
                            "content": {
                                "type": "string",
                                "description": "The content of the reply"
                            },
                            "subreddit": {
                                "type": "string",
                                "description": "The subreddit where the target is located"
                            }
                        },
                        "required": ["target_type", "target_id", "content", "subreddit"]
                    }
                }
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
                                "description": "The ID of the product to fetch"
                            }
                        },
                        "required": ["product_id"]
                    }
                }
            }
        ]
    
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
                    # Convert to schemas
                    product_schema = ProductInfoSchema.model_validate(product)
                    pipeline_schema = PipelineRunSchema.model_validate(pipeline_run)
                    reddit_schema = RedditPostSchema.model_validate(reddit_post)
                    
                    result.append(GeneratedProductSchema(
                        product_info=product_schema,
                        pipeline_run=pipeline_schema,
                        reddit_post=reddit_schema
                    ))
            
            return result
        except Exception as e:
            logger.error(f"Error fetching available products: {str(e)}")
            return []
    
    def fetch_generated_product(self, product_id: str) -> Optional[GeneratedProductSchema]:
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
            
            # Convert to schemas
            product_schema = ProductInfoSchema.model_validate(product)
            pipeline_schema = PipelineRunSchema.model_validate(pipeline_run)
            reddit_schema = RedditPostSchema.model_validate(reddit_post)
            
            return GeneratedProductSchema(
                product_info=product_schema,
                pipeline_run=pipeline_schema,
                reddit_post=reddit_schema
            )
        except Exception as e:
            logger.error(f"Error fetching product {product_id}: {str(e)}")
            return None
    
    def upvote(self, target_type: str, target_id: str, subreddit: str, product_info_id: int, reddit_post_id: int) -> Dict[str, Any]:
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
        try:
            # Create action record
            action = InteractionAgentAction(
                product_info_id=product_info_id,
                reddit_post_id=reddit_post_id,
                action_type='upvote',
                target_type=target_type,
                target_id=target_id,
                subreddit=subreddit,
                timestamp=datetime.now(timezone.utc)
            )
            self.session.add(action)
            
            # Execute the action
            if target_type == 'post':
                result = self.reddit_client.upvote_post(target_id)
            else:
                result = self.reddit_client.upvote_comment(target_id)
            
            # Update action record
            action.success = 'success'
            action.context_data = result
            self.session.commit()
            
            logger.info(f"Successfully upvoted {target_type} {target_id} in r/{subreddit}")
            return result
            
        except Exception as e:
            # Update action record with error
            if 'action' in locals():
                action.success = 'failed'
                action.error_message = str(e)
                self.session.commit()
            
            logger.error(f"Error upvoting {target_type} {target_id}: {str(e)}")
            return {'error': str(e)}
    
    def downvote(self, target_type: str, target_id: str, subreddit: str, product_info_id: int, reddit_post_id: int) -> Dict[str, Any]:
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
        try:
            # Create action record
            action = InteractionAgentAction(
                product_info_id=product_info_id,
                reddit_post_id=reddit_post_id,
                action_type='downvote',
                target_type=target_type,
                target_id=target_id,
                subreddit=subreddit,
                timestamp=datetime.now(timezone.utc)
            )
            self.session.add(action)
            
            # Execute the action
            if target_type == 'post':
                result = self.reddit_client.downvote_post(target_id)
            else:
                result = self.reddit_client.downvote_comment(target_id)
            
            # Update action record
            action.success = 'success'
            action.context_data = result
            self.session.commit()
            
            logger.info(f"Successfully downvoted {target_type} {target_id} in r/{subreddit}")
            return result
            
        except Exception as e:
            # Update action record with error
            if 'action' in locals():
                action.success = 'failed'
                action.error_message = str(e)
                self.session.commit()
            
            logger.error(f"Error downvoting {target_type} {target_id}: {str(e)}")
            return {'error': str(e)}
    
    def reply(self, target_type: str, target_id: str, content: str, subreddit: str, product_info_id: int, reddit_post_id: int) -> Dict[str, Any]:
        """
        Reply to a Reddit post or comment.
        
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
        try:
            # Create action record
            action = InteractionAgentAction(
                product_info_id=product_info_id,
                reddit_post_id=reddit_post_id,
                action_type='reply',
                target_type=target_type,
                target_id=target_id,
                content=content,
                subreddit=subreddit,
                timestamp=datetime.now(timezone.utc)
            )
            self.session.add(action)
            
            # Execute the action
            if target_type == 'post':
                result = self.reddit_client.comment_on_post(target_id, content)
            else:
                result = self.reddit_client.reply_to_comment(target_id, content)
            
            # Update action record
            action.success = 'success'
            action.context_data = result
            self.session.commit()
            
            logger.info(f"Successfully replied to {target_type} {target_id} in r/{subreddit}")
            return result
            
        except Exception as e:
            # Update action record with error
            if 'action' in locals():
                action.success = 'failed'
                action.error_message = str(e)
                self.session.commit()
            
            logger.error(f"Error replying to {target_type} {target_id}: {str(e)}")
            return {'error': str(e)}
    
    def process_interaction_request(self, prompt: str, product_info_id: int, reddit_post_id: int) -> Dict[str, Any]:
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
            product = self.session.query(ProductInfo).filter_by(id=product_info_id).first()
            reddit_post = self.session.query(RedditPost).filter_by(id=reddit_post_id).first()
            
            if not product or not reddit_post:
                return {'error': 'Product or Reddit post not found'}
            
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
            
            User Request: {prompt}
            
            Available tools:
            - upvote: Upvote a post or comment
            - downvote: Downvote a post or comment  
            - reply: Reply to a post or comment
            - fetch_generated_product: Get product details
            
            Only interact with the post/comment specified in the context. Be helpful and engaging.
            """
            
            # Call the LLM with function calling
            response = self.openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful Reddit interaction agent. Use the available tools to interact with Reddit content."},
                    {"role": "user", "content": context}
                ],
                tools=self.tools,
                tool_choice="auto"
            )
            
            # Process the response
            results = []
            for choice in response.choices:
                if choice.message.tool_calls:
                    for tool_call in choice.message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = tool_call.function.arguments
                        
                        # Parse arguments
                        import json
                        args = json.loads(function_args)
                        
                        # Execute the tool
                        if function_name == 'upvote':
                            result = self.upvote(
                                args['target_type'], 
                                args['target_id'], 
                                args['subreddit'],
                                product_info_id,
                                reddit_post_id
                            )
                        elif function_name == 'downvote':
                            result = self.downvote(
                                args['target_type'], 
                                args['target_id'], 
                                args['subreddit'],
                                product_info_id,
                                reddit_post_id
                            )
                        elif function_name == 'reply':
                            result = self.reply(
                                args['target_type'], 
                                args['target_id'], 
                                args['content'],
                                args['subreddit'],
                                product_info_id,
                                reddit_post_id
                            )
                        elif function_name == 'fetch_generated_product':
                            result = self.fetch_generated_product(args['product_id'])
                        else:
                            result = {'error': f'Unknown function: {function_name}'}
                        
                        results.append({
                            'function': function_name,
                            'arguments': args,
                            'result': result
                        })
            
            return {
                'success': True,
                'results': results,
                'llm_response': response.choices[0].message.content
            }
            
        except Exception as e:
            logger.error(f"Error processing interaction request: {str(e)}")
            return {'error': str(e)}
    
    def close(self):
        """Close the database session."""
        if self.session:
            self.session.close()
