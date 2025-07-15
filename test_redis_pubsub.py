#!/usr/bin/env python3
"""
Test script for Redis pub/sub functionality.

This script tests the Redis pub/sub integration for real-time task updates.
"""

import asyncio
import json
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.config import WEBSOCKET_GENERAL_UPDATES_CHANNEL, WEBSOCKET_TASK_UPDATES_CHANNEL
from app.redis_service import redis_service


async def test_redis_pubsub():
    """Test Redis pub/sub functionality."""
    print("Testing Redis pub/sub functionality...")

    try:
        # Connect to Redis
        await redis_service.connect()
        print("✓ Connected to Redis")

        # Test message received flag
        message_received = False
        received_message = None

        def on_message(message):
            nonlocal message_received, received_message
            message_received = True
            received_message = message
            print(f"✓ Received message: {message}")

        # Subscribe to channels
        redis_service.subscribe_to_channel(WEBSOCKET_TASK_UPDATES_CHANNEL, on_message)
        redis_service.subscribe_to_channel(
            WEBSOCKET_GENERAL_UPDATES_CHANNEL, on_message
        )
        print("✓ Subscribed to channels")

        # Start listening in background
        listener_task = asyncio.create_task(redis_service.start_listening())
        print("✓ Started Redis listener")

        # Wait a moment for listener to start
        await asyncio.sleep(1)

        # Test publishing a task update
        test_task_update = {
            "status": "in_progress",
            "message": "Test task update",
            "timestamp": asyncio.get_event_loop().time(),
        }

        await redis_service.publish_task_update("test-task-123", test_task_update)
        print("✓ Published task update")

        # Wait for message to be received
        await asyncio.sleep(2)

        if message_received:
            print("✓ Test passed: Message received successfully")
        else:
            print("✗ Test failed: No message received")
            return False

        # Test publishing a general update
        message_received = False
        test_general_update = {
            "type": "test_general_update",
            "message": "Test general update",
        }

        await redis_service.publish_general_update(test_general_update)
        print("✓ Published general update")

        # Wait for message to be received
        await asyncio.sleep(2)

        if message_received:
            print("✓ Test passed: General update received successfully")
        else:
            print("✗ Test failed: General update not received")
            return False

        # Clean up
        await redis_service.stop_listening()
        listener_task.cancel()
        await redis_service.disconnect()
        print("✓ Cleanup completed")

        return True

    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False


async def main():
    """Main test function."""
    print("Redis Pub/Sub Test")
    print("=" * 50)

    success = await test_redis_pubsub()

    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
