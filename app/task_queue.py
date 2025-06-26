"""
Task Queue system for managing pipeline execution tasks.

This module provides a database-driven task queue for managing pipeline execution,
including sponsored posts, front picks, and subreddit tier posts.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session

from app.db.models import PipelineTask, Sponsor
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class TaskQueue:
    """Database-driven task queue for pipeline execution."""

    def __init__(self, session: Session):
        """
        Initialize the task queue with a database session.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def add_task(
        self,
        task_type: str,
        subreddit: Optional[str] = None,
        sponsor_id: Optional[int] = None,
        priority: int = 0,
        scheduled_for: Optional[datetime] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> PipelineTask:
        """
        Add a new task to the queue.
        
        Args:
            task_type: Type of task (SPONSORED_POST, FRONT_PICK, CROSS_POST, SUBREDDIT_TIER_POST)
            subreddit: Target subreddit (optional)
            sponsor_id: Associated sponsor ID (optional)
            priority: Task priority (higher number = higher priority)
            scheduled_for: When to execute the task (optional)
            context_data: Additional context data (optional)
            
        Returns:
            PipelineTask: The created task
        """
        try:
            task = PipelineTask(
                type=task_type,
                subreddit=subreddit,
                sponsor_id=sponsor_id,
                status="pending",
                priority=priority,
                scheduled_for=scheduled_for,
                context_data=context_data,
            )
            
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)
            
            logger.info(f"Added task {task.id} of type {task_type} to queue")
            return task
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding task to queue: {str(e)}")
            raise

    def get_next_task(self) -> Optional[PipelineTask]:
        """
        Get the next task to execute based on priority and scheduling.
        
        Returns:
            PipelineTask: The next task to execute or None if no tasks available
        """
        try:
            now = datetime.now(timezone.utc)
            
            # Get the highest priority pending task that's ready to execute
            task = (
                self.session.query(PipelineTask)
                .filter(PipelineTask.status == "pending")
                .filter(
                    (PipelineTask.scheduled_for.is_(None)) | 
                    (PipelineTask.scheduled_for <= now)
                )
                .order_by(PipelineTask.priority.desc(), PipelineTask.created_at.asc())
                .first()
            )
            
            if task:
                logger.info(f"Retrieved task {task.id} of type {task.type} from queue")
                return task
            else:
                logger.debug("No tasks available in queue")
                return None
                
        except Exception as e:
            logger.error(f"Error getting next task: {str(e)}")
            raise

    def mark_completed(self, task_id: int, error_message: Optional[str] = None) -> bool:
        """
        Mark a task as completed or failed.
        
        Args:
            task_id: ID of the task to mark
            error_message: Error message if task failed
            
        Returns:
            bool: True if task was found and updated, False otherwise
        """
        try:
            task = self.session.query(PipelineTask).get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return False
            
            task.status = "failed" if error_message else "completed"
            task.completed_at = datetime.now(timezone.utc)
            if error_message:
                task.error_message = error_message
            
            self.session.commit()
            
            status = "failed" if error_message else "completed"
            logger.info(f"Marked task {task_id} as {status}")
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error marking task {task_id} as completed: {str(e)}")
            raise

    def mark_in_progress(self, task_id: int) -> bool:
        """
        Mark a task as in progress.
        
        Args:
            task_id: ID of the task to mark
            
        Returns:
            bool: True if task was found and updated, False otherwise
        """
        try:
            task = self.session.query(PipelineTask).get(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found")
                return False
            
            task.status = "in_progress"
            self.session.commit()
            
            logger.info(f"Marked task {task_id} as in progress")
            return True
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error marking task {task_id} as in progress: {str(e)}")
            raise

    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get the current status of the task queue.
        
        Returns:
            Dict: Queue status information
        """
        try:
            pending_count = self.session.query(PipelineTask).filter_by(status="pending").count()
            in_progress_count = self.session.query(PipelineTask).filter_by(status="in_progress").count()
            completed_count = self.session.query(PipelineTask).filter_by(status="completed").count()
            failed_count = self.session.query(PipelineTask).filter_by(status="failed").count()
            
            # Get next few tasks
            next_tasks = (
                self.session.query(PipelineTask)
                .filter(PipelineTask.status == "pending")
                .order_by(PipelineTask.priority.desc(), PipelineTask.created_at.asc())
                .limit(5)
                .all()
            )
            
            return {
                "pending": pending_count,
                "in_progress": in_progress_count,
                "completed": completed_count,
                "failed": failed_count,
                "total": pending_count + in_progress_count + completed_count + failed_count,
                "next_tasks": [
                    {
                        "id": task.id,
                        "type": task.type,
                        "subreddit": task.subreddit,
                        "priority": task.priority,
                        "created_at": task.created_at.isoformat(),
                        "scheduled_for": task.scheduled_for.isoformat() if task.scheduled_for else None,
                    }
                    for task in next_tasks
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting queue status: {str(e)}")
            raise

    def add_sponsored_task(self, sponsor_id: int, subreddit: str, priority: int = 10) -> PipelineTask:
        """
        Add a sponsored task to the queue.
        
        Args:
            sponsor_id: ID of the sponsor
            subreddit: Target subreddit
            priority: Task priority (sponsored tasks get high priority)
            
        Returns:
            PipelineTask: The created task
        """
        return self.add_task(
            task_type="SPONSORED_POST",
            subreddit=subreddit,
            sponsor_id=sponsor_id,
            priority=priority,
            context_data={"sponsored": True}
        )

    def add_front_pick_task(self, priority: int = 0) -> PipelineTask:
        """
        Add a front pick task to the queue.
        
        Args:
            priority: Task priority
            
        Returns:
            PipelineTask: The created task
        """
        return self.add_task(
            task_type="FRONT_PICK",
            priority=priority,
            context_data={"front_pick": True}
        )

    def add_subreddit_tier_task(self, subreddit: str, priority: int = 5) -> PipelineTask:
        """
        Add a subreddit tier task to the queue.
        
        Args:
            subreddit: Target subreddit
            priority: Task priority
            
        Returns:
            PipelineTask: The created task
        """
        return self.add_task(
            task_type="SUBREDDIT_TIER_POST",
            subreddit=subreddit,
            priority=priority,
            context_data={"subreddit_tier": True}
        ) 