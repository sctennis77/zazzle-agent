"""
WebSocket Manager for real-time task progress updates.

This module handles WebSocket connections for real-time updates
about commission task progress.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.
    
    This class handles:
    - WebSocket connections
    - Broadcasting updates to connected clients
    - Task progress notifications
    """
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections: Set[WebSocket] = set()
        self.task_subscriptions: Dict[str, Set[WebSocket]] = {}
        
        logger.info("WebSocket Manager initialized")
    
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
        """Broadcast a task update to all subscribed clients."""
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
        """Broadcast a general update to all connected clients."""
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