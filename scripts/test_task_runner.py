#!/usr/bin/env python3
"""
Test script for the task runner - creates a test task and runs the task runner
to process it independently of webhooks.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.database import SessionLocal
from app.db.models import PipelineTask, Subreddit
from app.task_queue import TaskQueue
from app.task_runner import TaskRunner
from app.utils.logging_config import setup_logging

# Set up logging
setup_logging(log_level="INFO", console_output=True)
logger = logging.getLogger(__name__)


def create_test_task(subreddit_name: str = "golf") -> int:
    """
    Create a test task in the database.
    
    Args:
        subreddit_name: Name of the subreddit to create task for
        
    Returns:
        int: The ID of the created task
    """
    session = SessionLocal()
    try:
        # Get or create subreddit
        subreddit = session.query(Subreddit).filter_by(subreddit_name=subreddit_name).first()
        if not subreddit:
            subreddit = Subreddit(
                subreddit_name=subreddit_name,
                display_name=subreddit_name,
                description=f"Test subreddit {subreddit_name}",
                subscribers=1000,
                created_at=datetime.utcnow()
            )
            session.add(subreddit)
            session.commit()
            session.refresh(subreddit)
        
        # Create test task
        task = PipelineTask(
            type="SUBREDDIT_POST",
            subreddit_id=subreddit.id,
            priority=10,
            status="pending",
            context_data={
                "test": True,
                "created_by": "test_script",
                "timestamp": datetime.utcnow().isoformat()
            },
            created_at=datetime.utcnow()
        )
        
        session.add(task)
        session.commit()
        session.refresh(task)
        
        logger.info(f"Created test task {task.id} for r/{subreddit_name}")
        return task.id
        
    finally:
        session.close()


async def test_task_runner():
    """Test the task runner by creating a task and running it once."""
    try:
        # Create a test task
        task_id = create_test_task("golf")
        logger.info(f"Created test task with ID: {task_id}")
        
        # Create task runner and run once
        runner = TaskRunner()
        logger.info("Starting task runner for single execution...")
        
        success = await runner.run_once()
        
        if success:
            logger.info("Task runner completed successfully!")
        else:
            logger.error("Task runner failed!")
            
        return success
        
    except Exception as e:
        logger.error(f"Error in test_task_runner: {str(e)}", exc_info=True)
        return False


def main():
    """Main function to run the test."""
    logger.info("Starting task runner test...")
    
    # Run the test
    success = asyncio.run(test_task_runner())
    
    if success:
        logger.info("✅ Task runner test completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Task runner test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 