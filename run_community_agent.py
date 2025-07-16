#!/usr/bin/env python3
"""
Standalone runner for the Clouvel Community Agent Service.

This script runs the autonomous Reddit community agent that embodies Queen Clouvel,
monitoring and engaging with subreddits to build and moderate the community.
"""

import asyncio
import argparse
import logging
import os
import signal
import sys
from typing import List

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.services.community_agent_service import CommunityAgentService


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("community_agent.log"),
        ],
    )


async def main():
    """Main entry point for the Community Agent runner."""
    parser = argparse.ArgumentParser(
        description="Run the Clouvel Community Agent Service"
    )
    parser.add_argument(
        "--subreddits",
        nargs="+",
        default=["clouvel"],
        help="Subreddits to monitor (default: clouvel)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no actual Reddit actions)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )
    parser.add_argument(
        "--stream-chunk-size",
        type=int,
        default=100,
        help="Number of items to buffer before processing",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Validate required environment variables
    required_env_vars = [
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET", 
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
        "OPENAI_API_KEY",
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please check your .env file or environment configuration")
        sys.exit(1)

    # Initialize the Community Agent Service
    service = CommunityAgentService(
        subreddit_names=args.subreddits,
        dry_run=args.dry_run,
        stream_chunk_size=args.stream_chunk_size,
    )

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        asyncio.create_task(service.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Print startup banner
    logger.info("=" * 60)
    logger.info("👑 QUEEN CLOUVEL'S ROYAL COMMUNITY AGENT 👑")
    logger.info("=" * 60)
    logger.info(f"Monitoring subreddits: {args.subreddits}")
    logger.info(f"Dry run mode: {args.dry_run}")
    logger.info(f"Log level: {args.log_level}")
    logger.info("=" * 60)

    try:
        # Start health server for Docker health checks
        await service.start_health_server()
        
        # Start the service
        await service.start()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
    except Exception as e:
        logger.error(f"Service error: {e}")
        sys.exit(1)
    finally:
        await service.stop()
        logger.info("👑 Queen Clouvel's service has ended. Farewell! 🐕✨")


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("Python 3.8 or higher is required")
        sys.exit(1)

    # Run the async main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👑 Queen Clouvel bids you farewell! 🐕✨")
        sys.exit(0)