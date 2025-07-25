"""
Redis service for pub/sub functionality.

This module handles Redis connections and pub/sub operations
for real-time task updates across multiple services.
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, Optional

import redis.asyncio as redis

from app.config import (
    REDIS_DB,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    REDIS_SSL,
    WEBSOCKET_GENERAL_UPDATES_CHANNEL,
    WEBSOCKET_TASK_UPDATES_CHANNEL,
)
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class RedisService:
    """
    Redis service for handling pub/sub operations.

    This class manages:
    - Redis connections
    - Publishing messages to channels
    - Subscribing to channels
    - Message handling
    """

    def __init__(self):
        """Initialize the Redis service."""
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self._subscribers: Dict[str, Callable] = {}
        self._running = False

        logger.info("Redis Service initialized")

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                ssl=REDIS_SSL,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test the connection
            await self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.pubsub:
            await self.pubsub.close()
            self.pubsub = None

        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None

        self._running = False
        logger.info("Disconnected from Redis")

    async def publish_task_update(self, task_id: str, update: Dict[str, Any]) -> None:
        """Publish a task update to the task updates channel."""
        if not self.redis_client:
            logger.warning("Redis client not connected, cannot publish task update")
            return

        try:
            message = {
                "type": "task_update",
                "task_id": task_id,
                "data": update,
                "timestamp": time.time(),
            }

            await self.redis_client.publish(
                WEBSOCKET_TASK_UPDATES_CHANNEL, json.dumps(message)
            )
            logger.info(f"Published task update for {task_id} to Redis")

        except Exception as e:
            logger.error(f"Failed to publish task update: {e}")

    async def publish_general_update(self, update: Dict[str, Any]) -> None:
        """Publish a general update to the general updates channel."""
        if not self.redis_client:
            logger.warning("Redis client not connected, cannot publish general update")
            return

        try:
            message = {
                "type": "general_update",
                "data": update,
                "timestamp": time.time(),
            }

            await self.redis_client.publish(
                WEBSOCKET_GENERAL_UPDATES_CHANNEL, json.dumps(message)
            )
            logger.info("Published general update to Redis")

        except Exception as e:
            logger.error(f"Failed to publish general update: {e}")

    def subscribe_to_channel(self, channel: str, callback: Callable) -> None:
        """Subscribe to a Redis channel with a callback function."""
        self._subscribers[channel] = callback
        logger.info(f"Subscribed to Redis channel: {channel}")

    async def start_listening(self) -> None:
        """Start listening for messages on subscribed channels."""
        if not self.redis_client:
            logger.error("Redis client not connected, cannot start listening")
            return

        if not self._subscribers:
            logger.warning("No subscribers registered, not starting listener")
            return

        try:
            self.pubsub = self.redis_client.pubsub()

            # Subscribe to all channels
            for channel in self._subscribers.keys():
                await self.pubsub.subscribe(channel)
                logger.info(f"Subscribed to Redis channel: {channel}")

            self._running = True

            # Start listening for messages
            async for message in self.pubsub.listen():
                if not self._running:
                    break

                logger.debug(f"Redis received message: {message}")

                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]

                    logger.info(
                        f"Processing Redis message on channel {channel}: {data}"
                    )

                    if channel in self._subscribers:
                        try:
                            # Parse the JSON message
                            parsed_data = json.loads(data)
                            logger.debug(f"Parsed Redis message: {parsed_data}")
                            callback = self._subscribers[channel]
                            if asyncio.iscoroutinefunction(callback):
                                await callback(parsed_data)
                            else:
                                callback(parsed_data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse Redis message: {e}")
                            logger.error(f"Raw message data: {data}")
                        except Exception as e:
                            logger.error(f"Error in subscriber callback: {e}")
                            logger.error(
                                f"Parsed data that caused error: {parsed_data}"
                            )
                    else:
                        logger.warning(f"No subscriber found for channel: {channel}")

        except Exception as e:
            logger.error(f"Error in Redis listener: {e}")
            self._running = False

    async def stop_listening(self) -> None:
        """Stop listening for messages."""
        self._running = False
        if self.pubsub:
            await self.pubsub.close()
            self.pubsub = None
        logger.info("Stopped Redis listener")

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        if not self.redis_client:
            return False

        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    async def acquire_lock(self, lock_key: str, timeout_seconds: int) -> bool:
        """
        Acquire a distributed lock with expiration.

        Args:
            lock_key: The key for the lock
            timeout_seconds: How long the lock should be held (in seconds)

        Returns:
            True if lock was acquired, False otherwise
        """
        if not self.redis_client:
            logger.error("Redis client not connected, cannot acquire lock")
            return False

        try:
            # Use SET with NX (only set if not exists) and EX (expiration)
            result = await self.redis_client.set(
                lock_key, "locked", nx=True, ex=timeout_seconds
            )
            if result:
                logger.info(f"Acquired lock: {lock_key}")
                return True
            else:
                logger.debug(f"Failed to acquire lock: {lock_key} (already held)")
                return False
        except Exception as e:
            logger.error(f"Error acquiring lock {lock_key}: {e}")
            return False

    async def release_lock(self, lock_key: str) -> bool:
        """
        Release a distributed lock.

        Args:
            lock_key: The key for the lock to release

        Returns:
            True if lock was released, False otherwise
        """
        if not self.redis_client:
            logger.error("Redis client not connected, cannot release lock")
            return False

        try:
            result = await self.redis_client.delete(lock_key)
            if result:
                logger.info(f"Released lock: {lock_key}")
                return True
            else:
                logger.debug(f"Lock {lock_key} was not held or already expired")
                return False
        except Exception as e:
            logger.error(f"Error releasing lock {lock_key}: {e}")
            return False


# Global Redis service instance
redis_service = RedisService()
