#!/usr/bin/env python3
"""
Test script for the Reddit interaction agent.

This script demonstrates how to use the RedditInteractionAgent to interact with Reddit posts.
"""

import os
import sys

from dotenv import load_dotenv

from app.agents.reddit_interaction_agent import RedditInteractionAgent
from app.utils.logging_config import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
setup_logging()


def main():
    """Main test function."""
    print("🧪 Testing Reddit Interaction Agent")
    print("=" * 50)

    # Initialize the agent
    agent = RedditInteractionAgent()

    try:
        # Get available products
        print("\n📦 Fetching available products...")
        products = agent.get_available_products()

        if not products:
            print("❌ No products found in database. Please run the pipeline first.")
            return

        print(f"✅ Found {len(products)} products")

        # Display products
        for i, product in enumerate(products[:3]):  # Show first 3 products
            print(f"\n{i+1}. Product: {product.product_info.theme}")
            print(f"   Subreddit: r/{product.reddit_post.subreddit}")
            print(f"   Post ID: {product.reddit_post.post_id}")
            print(f"   Post Title: {product.reddit_post.title}")

        # Test interaction with the first product
        if products:
            product = products[0]
            print(
                f"\n🎯 Testing interaction with product: {product.product_info.theme}"
            )

            # Test fetching product details
            print("\n📋 Fetching product details...")
            fetched_product = agent.fetch_generated_product(
                str(product.product_info.id)
            )
            if fetched_product:
                print(
                    f"✅ Successfully fetched product: {fetched_product.product_info.theme}"
                )
            else:
                print("❌ Failed to fetch product")

            # Test simple interaction request
            print("\n🤖 Testing simple interaction request...")
            simple_prompt = "Please upvote the original post"

            result = agent.process_interaction_request(
                prompt=simple_prompt,
                product_info_id=product.product_info.id,
                reddit_post_id=product.reddit_post.id,
            )

            if result.get("success"):
                print("✅ Simple interaction request processed successfully")
                print(f"🤖 LLM Response: {result.get('llm_response', 'No response')}")

                for action_result in result.get("results", []):
                    print(f"🔧 Function: {action_result['function']}")
                    print(f"📝 Arguments: {action_result['arguments']}")
                    print(f"📊 Result: {action_result['result']}")
            else:
                print(f"❌ Simple interaction request failed: {result.get('error')}")

            # Test complex interaction request with reply
            print("\n🤖 Testing complex interaction request with reply...")
            complex_prompt = f"Please upvote the original post and leave a helpful comment about the {product.product_info.theme} theme"

            result = agent.process_interaction_request(
                prompt=complex_prompt,
                product_info_id=product.product_info.id,
                reddit_post_id=product.reddit_post.id,
            )

            if result.get("success"):
                print("✅ Complex interaction request processed successfully")
                print(f"🤖 LLM Response: {result.get('llm_response', 'No response')}")

                for action_result in result.get("results", []):
                    print(f"🔧 Function: {action_result['function']}")
                    print(f"📝 Arguments: {action_result['arguments']}")
                    print(f"📊 Result: {action_result['result']}")
            else:
                print(f"❌ Complex interaction request failed: {result.get('error')}")

        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up
        agent.close()


if __name__ == "__main__":
    main()
