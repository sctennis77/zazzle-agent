"""
Task Monitor Service for detecting and handling stuck tasks.

This service monitors running tasks and detects when they become stuck,
then provides mechanisms to restart or recover them.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import PipelineTask
from app.task_manager import TaskManager
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class TaskMonitor:
    """Monitor and manage stuck tasks."""

    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self.monitoring = False
        self.monitor_task = None
        self.check_interval = 60  # Check every minute
        self.task_timeout = 300  # 5 minutes default timeout

    async def start_monitoring(self):
        """Start the task monitoring loop."""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Task monitoring started")

    async def stop_monitoring(self):
        """Stop the task monitoring loop."""
        if not self.monitoring:
            return

        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Task monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        try:
            while self.monitoring:
                await self._check_stuck_tasks()
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in task monitoring loop: {e}")

    async def _check_stuck_tasks(self):
        """Check for stuck tasks and handle them."""
        try:
            db = SessionLocal()
            try:
                stuck_tasks = self._find_stuck_tasks(db)

                for task in stuck_tasks:
                    logger.warning(f"Found stuck task {task.id} - handling...")
                    await self._handle_stuck_task(db, task)

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error checking stuck tasks: {e}")

    def _find_stuck_tasks(self, db: Session) -> List[PipelineTask]:
        """Find tasks that appear to be stuck."""
        now = datetime.now(timezone.utc)

        # Find tasks that are in_progress and either:
        # 1. Have no last_heartbeat and started_at is older than timeout
        # 2. Have last_heartbeat older than timeout
        # 3. Started more than timeout_seconds ago with no heartbeat

        stuck_tasks = []

        # Query for in_progress tasks
        in_progress_tasks = (
            db.query(PipelineTask).filter(PipelineTask.status == "in_progress").all()
        )

        for task in in_progress_tasks:
            is_stuck = False
            reason = ""

            # Check if task has timeout configuration
            timeout_seconds = getattr(task, "timeout_seconds", self.task_timeout)
            timeout_delta = timedelta(seconds=timeout_seconds)

            # Check last heartbeat
            if hasattr(task, "last_heartbeat") and task.last_heartbeat:
                if (
                    now - task.last_heartbeat.replace(tzinfo=timezone.utc)
                    > timeout_delta
                ):
                    is_stuck = True
                    reason = f"No heartbeat for {(now - task.last_heartbeat.replace(tzinfo=timezone.utc)).total_seconds():.0f} seconds"

            # Check started_at if no heartbeat
            elif hasattr(task, "started_at") and task.started_at:
                if now - task.started_at.replace(tzinfo=timezone.utc) > timeout_delta:
                    is_stuck = True
                    reason = f"Started {(now - task.started_at.replace(tzinfo=timezone.utc)).total_seconds():.0f} seconds ago with no heartbeat"

            # Check created_at as fallback
            elif task.created_at:
                if now - task.created_at.replace(tzinfo=timezone.utc) > timeout_delta:
                    is_stuck = True
                    reason = f"Created {(now - task.created_at.replace(tzinfo=timezone.utc)).total_seconds():.0f} seconds ago, still in progress"

            if is_stuck:
                logger.warning(f"Task {task.id} appears stuck: {reason}")
                stuck_tasks.append(task)

        return stuck_tasks

    async def _handle_stuck_task(self, db: Session, task: PipelineTask):
        """Handle a stuck task by attempting to restart it."""
        try:
            # Check retry count
            retry_count = getattr(task, "retry_count", 0)
            max_retries = getattr(task, "max_retries", 2)

            if retry_count >= max_retries:
                logger.error(
                    f"Task {task.id} has exceeded max retries ({max_retries}), marking as failed"
                )
                await self._mark_task_failed(
                    db, task, "Task stuck and exceeded max retries"
                )
                return

            # Increment retry count
            if hasattr(task, "retry_count"):
                task.retry_count = retry_count + 1

            # Reset task status and timing
            task.status = "pending"
            if hasattr(task, "started_at"):
                task.started_at = None
            if hasattr(task, "last_heartbeat"):
                task.last_heartbeat = None

            db.commit()

            logger.info(
                f"Reset stuck task {task.id} to pending (retry {retry_count + 1}/{max_retries})"
            )

            # Restart the task
            await self._restart_task(task)

        except Exception as e:
            logger.error(f"Error handling stuck task {task.id}: {e}")

    async def _restart_task(self, task: PipelineTask):
        """Restart a task using the task manager."""
        try:
            if task.donation_id:
                # This is a commission task, restart it
                task_data = task.context_data or {}
                self.task_manager.create_commission_task(task.donation_id, task_data)
                logger.info(
                    f"Restarted commission task {task.id} for donation {task.donation_id}"
                )
            else:
                logger.warning(
                    f"Task {task.id} is not a commission task, cannot restart automatically"
                )

        except Exception as e:
            logger.error(f"Error restarting task {task.id}: {e}")

    async def _mark_task_failed(
        self, db: Session, task: PipelineTask, error_message: str
    ):
        """Mark a task as failed."""
        try:
            task.status = "failed"
            task.error_message = error_message
            task.completed_at = datetime.now(timezone.utc)

            db.commit()

            # Handle refund if this is a commission task
            if task.donation_id:
                self.task_manager.handle_task_failure(db, task.id, error_message)

            logger.info(f"Marked task {task.id} as failed: {error_message}")

        except Exception as e:
            logger.error(f"Error marking task {task.id} as failed: {e}")

    def get_monitoring_status(self) -> Dict[str, any]:
        """Get current monitoring status."""
        return {
            "monitoring": self.monitoring,
            "check_interval": self.check_interval,
            "task_timeout": self.task_timeout,
            "monitor_task_running": self.monitor_task is not None
            and not self.monitor_task.done(),
        }

    async def check_stuck_tasks_once(self) -> Dict[str, any]:
        """Perform a one-time check for stuck tasks."""
        db = SessionLocal()
        try:
            stuck_tasks = self._find_stuck_tasks(db)

            result = {"stuck_tasks_found": len(stuck_tasks), "tasks": []}

            for task in stuck_tasks:
                task_info = {
                    "task_id": task.id,
                    "status": task.status,
                    "created_at": (
                        task.created_at.isoformat() if task.created_at else None
                    ),
                    "started_at": getattr(task, "started_at", None),
                    "last_heartbeat": getattr(task, "last_heartbeat", None),
                    "retry_count": getattr(task, "retry_count", 0),
                    "max_retries": getattr(task, "max_retries", 2),
                    "donation_id": task.donation_id,
                }

                if task_info["started_at"]:
                    task_info["started_at"] = task_info["started_at"].isoformat()
                if task_info["last_heartbeat"]:
                    task_info["last_heartbeat"] = task_info[
                        "last_heartbeat"
                    ].isoformat()

                result["tasks"].append(task_info)

            return result

        finally:
            db.close()
