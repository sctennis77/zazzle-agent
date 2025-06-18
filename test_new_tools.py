#!/usr/bin/env python3
"""
Simple test script to verify the new context tools work correctly.
"""

import os
import sys
from app.agents.reddit_interaction_agent import RedditInteractionAgent
from app.models import InteractionActionType
from app.db.database import SessionLocal
from app.db.models import ProductInfo

# Hardcode the test database URL
os.environ['DATABASE_URL'] = 'sqlite:///test_interaction_agent.db'
os.environ['REDDIT_MODE'] = 'dryrun'
# Use the real OpenAI API key from environment instead of overriding


def get_test_product_data():
    """Get a real product and its associated reddit post from the test database."""
    db = SessionLocal()
    try:
        product = db.query(ProductInfo).first()
        if product:
            return product.id, product.reddit_post_id
        else:
            raise Exception("No products found in test database")
    finally:
        db.close()


def test_new_tools():
    """Test the new get_post_context and get_comment_context tools."""
    agent = RedditInteractionAgent()
    print("Testing new context tools...")
    
    # Get a real product ID and reddit post ID from the database
    try:
        product_id, reddit_post_id = get_test_product_data()
        print(f"Using product ID: {product_id}, reddit post ID: {reddit_post_id}")
    except Exception as e:
        print(f"❌ Failed to get product data: {e}")
        return
    
    print("\n1. Testing get_post_context...")
    try:
        result = agent.get_post_context("1leg4ab", product_id, reddit_post_id)
        print(f"✅ get_post_context result: {type(result)}")
        print(f"   Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
    except Exception as e:
        print(f"❌ get_post_context failed: {e}")

    print("\n2. Testing get_comment_context...")
    try:
        result = agent.get_comment_context("dummy_comment_id", product_id, reddit_post_id)
        print(f"✅ get_comment_context result: {type(result)}")
        print(f"   Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
    except Exception as e:
        print(f"❌ get_comment_context failed: {e}")

    print("\n3. Verifying tools are in the tools list...")
    tools = [tool['function']['name'] for tool in agent.tools]
    print(f"Available tools: {tools}")
    print(f"{'✅' if 'get_post_context' in tools else '❌'} get_post_context tool found")
    print(f"{'✅' if 'get_comment_context' in tools else '❌'} get_comment_context tool found")

    print("\n4. Verifying enum values...")
    print(f"GET_POST_CONTEXT enum: {InteractionActionType.GET_POST_CONTEXT.value}")
    print(f"GET_COMMENT_CONTEXT enum: {InteractionActionType.GET_COMMENT_CONTEXT.value}")

    print("\n5. Testing available actions functionality...")
    try:
        # Test fetch_generated_product with available actions
        product_result = agent.fetch_generated_product(str(product_id))
        if product_result and product_result.product_info.available_actions:
            print(f"✅ Available actions found: {product_result.product_info.available_actions}")
        else:
            print("⚠️  No available actions found (this is normal for a fresh product)")
        
        # Test calculate_available_actions directly
        available_actions = agent.calculate_available_actions(product_id)
        print(f"✅ Direct calculation result: {available_actions}")
        
        # Test is_action_available
        is_upvote_available = agent.is_action_available(product_id, InteractionActionType.UPVOTE.value)
        print(f"✅ Upvote available: {is_upvote_available}")
        
    except Exception as e:
        print(f"❌ Available actions test failed: {e}")

    print("\n6. Testing generate_non_marketing_reply...")
    try:
        # Test the new non-marketing reply generation
        reddit_context = "This is a test post about vehicle speed estimation from camera feeds. The OP is asking for help with their physics project."
        result = agent.generate_non_marketing_reply(str(product_id), reddit_context)
        print(f"✅ generate_non_marketing_reply result: {result[:100]}...")
        
        # Check if it's available again (should not be)
        is_available = agent.is_action_available(product_id, InteractionActionType.GENERATE_NON_MARKETING_REPLY.value)
        print(f"✅ Non-marketing reply still available: {is_available}")
        
    except Exception as e:
        print(f"❌ generate_non_marketing_reply test failed: {e}")

    print("\n✅ All tests completed!")


if __name__ == "__main__":
    test_new_tools() 