"""
Task Queue system for managing pipeline execution tasks.

This module provides a database-driven task queue for managing pipeline execution,
including sponsored posts, front picks, and subreddit tier posts.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import Donation, PipelineTask
from app.subreddit_service import get_subreddit_service
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
        subreddit_id: int,
        donation_id: Optional[int] = None,
        priority: int = 0,
        scheduled_for: Optional[datetime] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> PipelineTask:
        """
        Add a task to the queue.

        Args:
            task_type: Type of task (SUBREDDIT_POST)
            subreddit_id: Target subreddit ID
            donation_id: Associated donation ID
            priority: Task priority (higher number = higher priority)
            scheduled_for: When to execute the task
            context_data: Additional context data

        Returns:
            PipelineTask: The created task

        Raises:
            ValueError: If task type is invalid or subreddit_id is missing
        """
        try:
            # Validate task type
            if task_type != "SUBREDDIT_POST":
                raise ValueError(
                    f"Invalid task type: {task_type}. Only SUBREDDIT_POST is supported"
                )

            # Validate subreddit_id
            if not subreddit_id:
                raise ValueError("Subreddit ID is required")

            task = PipelineTask(
                type=task_type,
                subreddit_id=subreddit_id,
                donation_id=donation_id,
                priority=priority,
                scheduled_for=scheduled_for,
                context_data=context_data or {},
                status="pending",
            )

            self.session.add(task)
            self.session.commit()

            # Get subreddit name for logging
            subreddit_name = (
                task.subreddit.subreddit_name
                if task.subreddit
                else f"ID:{subreddit_id}"
            )
            logger.info(
                f"Added task {task.id} of type {task_type} for r/{subreddit_name} to queue"
            )
            return task

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding task to queue: {str(e)}")
            raise

    def add_task_by_name(
        self,
        task_type: str,
        subreddit_name: str,
        donation_id: Optional[int] = None,
        priority: int = 0,
        scheduled_for: Optional[datetime] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> PipelineTask:
        """
        Add a task to the queue using subreddit name (creates subreddit entity if needed).

        Args:
            task_type: Type of task (SUBREDDIT_POST)
            subreddit_name: Target subreddit name (e.g., "golf", "all")
            donation_id: Associated donation ID
            priority: Task priority (higher number = higher priority)
            scheduled_for: When to execute the task
            context_data: Additional context data

        Returns:
            PipelineTask: The created task
        """
        # Get or create subreddit entity
        subreddit_service = get_subreddit_service()
        subreddit = subreddit_service.get_or_create_subreddit(
            subreddit_name, self.session
        )

        return self.add_task(
            task_type=task_type,
            subreddit_id=subreddit.id,
            donation_id=donation_id,
            priority=priority,
            scheduled_for=scheduled_for,
            context_data=context_data,
        )

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
                    (PipelineTask.scheduled_for.is_(None))
                    | (PipelineTask.scheduled_for <= now)
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
            pending_count = (
                self.session.query(PipelineTask).filter_by(status="pending").count()
            )
            in_progress_count = (
                self.session.query(PipelineTask).filter_by(status="in_progress").count()
            )
            completed_count = (
                self.session.query(PipelineTask).filter_by(status="completed").count()
            )
            failed_count = (
                self.session.query(PipelineTask).filter_by(status="failed").count()
            )

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
                "total": pending_count
                + in_progress_count
                + completed_count
                + failed_count,
                "next_tasks": [
                    {
                        "id": task.id,
                        "type": task.type,
                        "subreddit": (
                            task.subreddit.subreddit_name
                            if task.subreddit
                            else f"ID:{task.subreddit_id}"
                        ),
                        "priority": task.priority,
                        "created_at": task.created_at.isoformat(),
                        "scheduled_for": (
                            task.scheduled_for.isoformat()
                            if task.scheduled_for
                            else None
                        ),
                    }
                    for task in next_tasks
                ],
            }

        except Exception as e:
            logger.error(f"Error getting queue status: {str(e)}")
            raise

    def add_subreddit_task(
        self, subreddit_name: str, priority: int = 5
    ) -> PipelineTask:
        """
        Add a subreddit task to the queue.

        Args:
            subreddit_name: Target subreddit name (use "all" for front page)
            priority: Task priority

        Returns:
            PipelineTask: The created task
        """
        return self.add_task_by_name(
            task_type="SUBREDDIT_POST",
            subreddit_name=subreddit_name,
            priority=priority,
            context_data={"subreddit_task": True},
        )

    def add_front_task(self, priority: int = 0) -> PipelineTask:
        """
        Add a front page task to the queue (uses "all" subreddit).

        Args:
            priority: Task priority

        Returns:
            PipelineTask: The created task
        """
        return self.add_task_by_name(
            task_type="SUBREDDIT_POST",
            subreddit_name="all",
            priority=priority,
            context_data={"front_task": True},
        )

    def cleanup_stuck_tasks(self, max_duration_minutes: int = 30) -> int:
        """
        Clean up tasks that have been stuck in 'in_progress' for too long.

        Args:
            max_duration_minutes: Maximum time a task can be in progress before being reset

        Returns:
            int: Number of tasks cleaned up
        """
        try:
            from datetime import timedelta

            cutoff_time = datetime.now(timezone.utc) - timedelta(
                minutes=max_duration_minutes
            )

            stuck_tasks = (
                self.session.query(PipelineTask)
                .filter(PipelineTask.status == "in_progress")
                .filter(PipelineTask.created_at < cutoff_time)
                .all()
            )

            cleaned_count = 0
            for task in stuck_tasks:
                task.status = "pending"  # Reset to pending so it can be retried
                task.error_message = f"Task was stuck in progress for {max_duration_minutes} minutes, reset to pending"
                cleaned_count += 1
                logger.warning(
                    f"Reset stuck task {task.id} (type: {task.type}) back to pending"
                )

            if cleaned_count > 0:
                self.session.commit()
                logger.info(f"Cleaned up {cleaned_count} stuck tasks")

            return cleaned_count

        except Exception as e:
            self.session.rollback()
            logger.error(f"Error cleaning up stuck tasks: {str(e)}")
            raise
