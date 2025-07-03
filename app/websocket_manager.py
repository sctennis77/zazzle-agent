"""
WebSocket Manager for real-time task progress updates.

This module handles WebSocket connections for real-time updates
about commission task progress, using Redis pub/sub for cross-service communication.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from app.utils.logging_config import get_logger
from app.redis_service import redis_service
from app.config import WEBSOCKET_TASK_UPDATES_CHANNEL, WEBSOCKET_GENERAL_UPDATES_CHANNEL

logger = get_logger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.
    
    This class handles:
    - WebSocket connections
    - Broadcasting updates to connected clients
    - Task progress notifications
    - Redis pub/sub integration for cross-service updates
    """
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections: Set[WebSocket] = set()
        self.task_subscriptions: Dict[str, Set[WebSocket]] = {}
        self._redis_listener_task: Optional[asyncio.Task] = None
        
        logger.info("WebSocket Manager initialized")
    
    async def start(self) -> None:
        """Start the WebSocket manager and Redis listener."""
        try:
            # Connect to Redis
            await redis_service.connect()
            
            # Subscribe to Redis channels
            redis_service.subscribe_to_channel(
                WEBSOCKET_TASK_UPDATES_CHANNEL,
                self._handle_redis_task_update
            )
            redis_service.subscribe_to_channel(
                WEBSOCKET_GENERAL_UPDATES_CHANNEL,
                self._handle_redis_general_update
            )
            
            # Start Redis listener
            self._redis_listener_task = asyncio.create_task(
                redis_service.start_listening()
            )
            
            logger.info("WebSocket Manager started with Redis integration")
            
        except Exception as e:
            logger.warning(f"Redis not available, starting WebSocket Manager without Redis: {e}")
            logger.info("WebSocket Manager started without Redis integration")
            # Continue without Redis - WebSocket functionality will still work
            # but cross-service communication will be limited
    
    async def stop(self) -> None:
        """Stop the WebSocket manager and Redis listener."""
        if self._redis_listener_task:
            self._redis_listener_task.cancel()
            try:
                await self._redis_listener_task
            except asyncio.CancelledError:
                pass
        
        await redis_service.stop_listening()
        await redis_service.disconnect()
        
        logger.info("WebSocket Manager stopped")
    
    async def _handle_redis_task_update(self, message: Dict[str, Any]) -> None:
        """Handle task updates from Redis."""
        try:
            logger.info(f"Received Redis task update message: {message}")
            task_id = message.get("task_id")
            data = message.get("data", {})
            
            if task_id:
                await self._broadcast_to_task_subscribers(task_id, data)
                logger.info(f"Handled Redis task update for {task_id}")
            else:
                logger.warning(f"Redis task update message missing task_id: {message}")
            
        except Exception as e:
            logger.error(f"Error handling Redis task update: {e}")
            logger.error(f"Message that caused error: {message}")
    
    async def _handle_redis_general_update(self, message: Dict[str, Any]) -> None:
        """Handle general updates from Redis."""
        try:
            data = message.get("data", {})
            await self._broadcast_to_all_connections(data)
            logger.info("Handled Redis general update")
            
        except Exception as e:
            logger.error(f"Error handling Redis general update: {e}")
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        
        # Remove from task subscriptions
        for task_id in list(self.task_subscriptions.keys()):
            self.task_subscriptions[task_id].discard(websocket)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def subscribe_to_task(self, websocket: WebSocket, task_id: str):
        """Subscribe a WebSocket to task updates."""
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        
        self.task_subscriptions[task_id].add(websocket)
        logger.info(f"WebSocket subscribed to task {task_id}")
    
    async def unsubscribe_from_task(self, websocket: WebSocket, task_id: str):
        """Unsubscribe a WebSocket from task updates."""
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(websocket)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
        
        logger.info(f"WebSocket unsubscribed from task {task_id}")
    
    async def broadcast_task_update(self, task_id: str, update: Dict[str, Any]):
        """Broadcast a task update to Redis (for cross-service communication)."""
        try:
            await redis_service.publish_task_update(task_id, update)
        except Exception as e:
            logger.warning(f"Redis not available for task update broadcast: {e}")
            # Fallback to direct WebSocket broadcast
            await self._broadcast_to_task_subscribers(task_id, update)
    
    async def _broadcast_to_task_subscribers(self, task_id: str, update: Dict[str, Any]):
        """Broadcast a task update to all subscribed clients (internal method)."""
        if task_id not in self.task_subscriptions:
            return
        
        message = {
            "type": "task_update",
            "task_id": task_id,
            "data": update
        }
        
        disconnected = set()
        for websocket in self.task_subscriptions[task_id]:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending task update: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
        
        logger.info(f"Broadcasted task update for {task_id} to {len(self.task_subscriptions[task_id])} clients")
    
    async def broadcast_general_update(self, update: Dict[str, Any]):
        """Broadcast a general update to Redis (for cross-service communication)."""
        try:
            await redis_service.publish_general_update(update)
        except Exception as e:
            logger.warning(f"Redis not available for general update broadcast: {e}")
            # Fallback to direct WebSocket broadcast
            await self._broadcast_to_all_connections(update)
    
    async def _broadcast_to_all_connections(self, update: Dict[str, Any]):
        """Broadcast a general update to all connected clients (internal method)."""
        message = {
            "type": "general_update",
            "data": update
        }
        
        disconnected = set()
        for websocket in self.active_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending general update: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
        
        logger.info(f"Broadcasted general update to {len(self.active_connections)} clients")
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a personal message to a specific WebSocket."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_task_subscriber_count(self, task_id: str) -> int:
        """Get the number of subscribers for a task."""
        return len(self.task_subscriptions.get(task_id, set()))


# Global WebSocket manager instance
websocket_manager = WebSocketManager() 