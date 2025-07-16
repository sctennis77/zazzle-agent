"""
Community Agent Service - Production orchestrator for ClouvelCommunityAgent.

Provides streaming Reddit monitoring and autonomous community management.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import praw
import redis
from praw.models import Comment, Submission

from app.agents.clouvel_community_agent import ClouvelCommunityAgent
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)


class CommunityAgentService:
    """Production service that orchestrates the ClouvelCommunityAgent with streaming."""

    def __init__(
        self,
        subreddit_names: List[str] = None,
        dry_run: bool = True,
        stream_chunk_size: int = 100,
    ):
        """
        Initialize the Community Agent Service.
        
        Args:
            subreddit_names: List of subreddits to monitor (default: ["clouvel"])
            dry_run: Whether to run in dry-run mode (no actual Reddit actions)
            stream_chunk_size: Number of items to buffer before processing
        """
        self.subreddit_names = subreddit_names or ["clouvel"]
        self.dry_run = dry_run
        self.stream_chunk_size = stream_chunk_size
        self.running = False
        
        # Initialize Reddit client for streaming
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
            user_agent=os.getenv(
                "REDDIT_USER_AGENT", "clouvel-agent by u/queen_clouvel"
            ),
        )
        
        # Initialize Redis for real-time updates
        self.redis_client = None
        if os.getenv("REDIS_URL"):
            try:
                self.redis_client = redis.from_url(
                    os.getenv("REDIS_URL"), decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self.redis_client = None
        
        # Create agents for each subreddit
        self.agents: Dict[str, ClouvelCommunityAgent] = {}
        for subreddit_name in self.subreddit_names:
            self.agents[subreddit_name] = ClouvelCommunityAgent(
                subreddit_name=subreddit_name, dry_run=dry_run
            )
        
        logger.info(
            f"Initialized CommunityAgentService for subreddits: {self.subreddit_names}"
        )

    def _publish_agent_update(self, subreddit_name: str, update: Dict):
        """Publish real-time update via Redis for WebSocket broadcasting."""
        if not self.redis_client:
            return
            
        try:
            channel = f"community_agent:{subreddit_name}"
            message = {
                "type": "community_agent_action",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "subreddit": subreddit_name,
                "data": update,
            }
            self.redis_client.publish(channel, json.dumps(message))
            logger.debug(f"Published update to {channel}: {update}")
        except Exception as e:
            logger.error(f"Failed to publish update: {e}")

    async def _process_stream_item(self, item, item_type: str, subreddit_name: str):
        """Process a single item from the Reddit stream."""
        try:
            agent = self.agents[subreddit_name]
            
            # Check rate limits before processing
            with agent._get_db_session() as session:
                state = agent._get_or_create_state(session)
                if not agent._check_rate_limits(session, state):
                    logger.info(f"Rate limit reached for {subreddit_name}, skipping")
                    return

            # Decide actions based on the item
            if item_type == "submission":
                actions = await agent.decide_actions([item], [])
            else:  # comment
                actions = await agent.decide_actions([], [item])
            
            if not actions:
                return
                
            logger.info(
                f"Processing {len(actions)} actions for {item_type} {item.id} in {subreddit_name}"
            )
            
            # Execute actions and log results
            with agent._get_db_session() as session:
                state = agent._get_or_create_state(session)
                
                for action in actions:
                    # Check rate limits before each action
                    if not agent._check_rate_limits(session, state):
                        logger.warning("Rate limit reached during action processing")
                        break
                    
                    # Execute the action
                    result = await agent.execute_action(action)
                    
                    # Log action to database
                    db_action = agent.log_action(session, action, result)
                    
                    # Increment action count if successful
                    if result.get("success"):
                        agent._increment_action_count(session, state)
                    
                    # Publish real-time update
                    update = {
                        "action_id": db_action.id,
                        "action_type": action.get("action"),
                        "target_type": action.get("target_type"),
                        "target_id": action.get("target_id"),
                        "success": result.get("success"),
                        "mood": action.get("mood"),
                        "reasoning": action.get("reasoning"),
                        "dry_run": self.dry_run,
                    }
                    self._publish_agent_update(subreddit_name, update)
                    
                    # Brief delay between actions for politeness
                    await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error processing {item_type} {item.id}: {e}")

    async def _stream_subreddit(self, subreddit_name: str):
        """Stream a single subreddit for new posts and comments."""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            logger.info(f"Starting stream for r/{subreddit_name}")
            
            # Create combined stream of submissions and comments
            stream = praw.models.util.stream_generator(
                lambda **kwargs: [
                    *subreddit.new(limit=25),
                    *subreddit.comments(limit=50)
                ],
                max_wait=60,  # Wait up to 60 seconds between API calls
                skip_existing=True,
            )
            
            async for item in self._async_wrapper(stream):
                if not self.running:
                    break
                    
                # Determine item type and process
                if isinstance(item, Submission):
                    await self._process_stream_item(item, "submission", subreddit_name)
                elif isinstance(item, Comment):
                    await self._process_stream_item(item, "comment", subreddit_name)
                    
        except Exception as e:
            logger.error(f"Error streaming r/{subreddit_name}: {e}")
            if self.running:
                # Wait before retrying
                await asyncio.sleep(30)
                await self._stream_subreddit(subreddit_name)

    async def _async_wrapper(self, sync_generator):
        """Wrap synchronous PRAW generator for async usage."""
        def run_sync():
            try:
                return next(sync_generator)
            except StopIteration:
                return None
        
        while self.running:
            try:
                # Run the synchronous operation in a thread pool
                item = await asyncio.get_event_loop().run_in_executor(None, run_sync)
                if item is None:
                    await asyncio.sleep(1)
                    continue
                yield item
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await asyncio.sleep(5)

    async def start(self):
        """Start the Community Agent Service with streaming."""
        if self.running:
            logger.warning("Service is already running")
            return
            
        self.running = True
        logger.info("Starting Community Agent Service...")
        
        # Publish startup notification
        for subreddit_name in self.subreddit_names:
            startup_update = {
                "action_type": "service_started",
                "message": f"Queen Clouvel's royal presence activated for r/{subreddit_name}",
                "dry_run": self.dry_run,
            }
            self._publish_agent_update(subreddit_name, startup_update)
        
        # Start streaming tasks for each subreddit
        tasks = []
        for subreddit_name in self.subreddit_names:
            task = asyncio.create_task(self._stream_subreddit(subreddit_name))
            tasks.append(task)
        
        try:
            # Wait for all streaming tasks
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Service cancelled")
        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            self.running = False

    async def stop(self):
        """Stop the Community Agent Service."""
        logger.info("Stopping Community Agent Service...")
        self.running = False
        
        # Publish shutdown notification
        for subreddit_name in self.subreddit_names:
            shutdown_update = {
                "action_type": "service_stopped",
                "message": f"Queen Clouvel takes a royal nap, watching over r/{subreddit_name} from afar",
                "dry_run": self.dry_run,
            }
            self._publish_agent_update(subreddit_name, shutdown_update)

    def get_service_status(self) -> Dict:
        """Get current service status and statistics."""
        status = {
            "running": self.running,
            "subreddits": self.subreddit_names,
            "dry_run": self.dry_run,
            "redis_connected": self.redis_client is not None,
            "agents": {},
        }
        
        # Get stats from each agent
        for subreddit_name, agent in self.agents.items():
            try:
                community_stats = agent.get_community_stats()
                
                # Get recent actions from database
                with agent._get_db_session() as session:
                    from app.db.models import CommunityAgentAction
                    recent_actions = (
                        session.query(CommunityAgentAction)
                        .filter_by(subreddit_id=agent._get_or_create_subreddit(session).id)
                        .order_by(CommunityAgentAction.timestamp.desc())
                        .limit(10)
                        .all()
                    )
                    
                    status["agents"][subreddit_name] = {
                        "community_stats": community_stats,
                        "recent_actions_count": len(recent_actions),
                        "last_action": (
                            recent_actions[0].timestamp.isoformat()
                            if recent_actions
                            else None
                        ),
                    }
            except Exception as e:
                status["agents"][subreddit_name] = {"error": str(e)}
        
        return status

    def get_health_status(self) -> Dict:
        """Get health status for Docker health checks."""
        status = self.get_service_status()
        return {
            "status": "healthy" if status["running"] else "unhealthy",
            "service": status
        }

    async def start_health_server(self):
        """Start a simple health check server on port 8001."""
        # For Docker health checks, we'll write status to a file instead
        # This is simpler than adding aiohttp dependency
        import json
        import asyncio
        
        async def write_health_status():
            while self.running:
                try:
                    health_status = self.get_health_status()
                    with open("/tmp/community_agent_health.json", "w") as f:
                        json.dump(health_status, f)
                    await asyncio.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    logger.error(f"Error writing health status: {e}")
                    await asyncio.sleep(5)
        
        asyncio.create_task(write_health_status())
        logger.info("Health status monitoring started (writing to /tmp/community_agent_health.json)")