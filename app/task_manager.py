"""
Unified Task Manager for commission processing.

This module provides a unified interface for task management that can use
both Kubernetes Jobs and direct execution as fallback
"""

import asyncio
import json
import logging
import threading
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.commission_worker import CommissionWorker
from app.db.database import SessionLocal
from app.db.models import Donation, PipelineTask
from app.utils.logging_config import get_logger

# Optional k8s dependency
try:
    from app.k8s_job_manager import K8sJobManager
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False
    K8sJobManager = None

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskManager:
    """Unified task manager for commission processing."""

    def __init__(self):
        """Initialize the task manager."""
        if K8S_AVAILABLE:
            self.k8s_manager = K8sJobManager()
            self.use_k8s = self.k8s_manager.enabled
        else:
            self.k8s_manager = None
            self.use_k8s = False
        logger.info(f"Task Manager initialized - K8s available: {self.use_k8s}")

    def create_commission_task(
        self, donation_id: int, task_data: Dict[str, Any], db: Optional[Session] = None
    ) -> str:
        """
        Create a commission task using either K8s Jobs or direct execution.

        Args:
            donation_id: The donation ID
            task_data: Task configuration data
            db: Optional database session to use (if not provided, creates a new one)

        Returns:
            Task ID
        """
        # Create the pipeline task in the database
        task_id = self._create_pipeline_task(donation_id, task_data, db)

        # Broadcast new task creation to all WebSocket clients
        self._broadcast_task_creation(task_id, donation_id, db)

        if self.use_k8s:
            # Use Kubernetes Jobs
            logger.info(
                f"Creating K8s Job for task {task_id} (donation_id={donation_id})"
            )
            self.k8s_manager.create_commission_job(task_id, donation_id, task_data)
        else:
            # Use direct execution fallback
            logger.info(
                f"Running commission task {task_id} directly (donation_id={donation_id})"
            )
            self._run_commission_task_directly(task_id, donation_id, task_data)

        return task_id

    def _broadcast_task_creation(
        self, task_id: str, donation_id: int, db: Optional[Session] = None
    ):
        """Broadcast new task creation to all WebSocket clients."""
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            # Get the task and related data
            task = db.query(PipelineTask).filter(
                PipelineTask.id == task_id
            ).first()
            if not task:
                logger.warning(f"Task {task_id} not found for broadcasting")
                return

            donation = task.donation
            subreddit = task.subreddit

            # Create task info for broadcasting
            task_info = {
                "task_id": str(task.id),
                "status": task.status,
                "created_at": (
                    task.created_at.isoformat() if task.created_at else None
                ),
                "donation_id": task.donation_id,
                "stage": "pending",
                "message": "Commission created",
                "progress": 0,
                "reddit_username": (
                    donation.reddit_username
                    if donation
                    and donation.reddit_username
                    and not donation.is_anonymous
                    else "Anonymous"
                ),
                "tier": donation.tier if donation else None,
                "subreddit": subreddit.subreddit_name if subreddit else None,
                "amount_usd": float(donation.amount_usd) if donation else None,
                "is_anonymous": donation.is_anonymous if donation else None,
                "timestamp": (
                    task.created_at.timestamp() if task.created_at else None
                ),
            }

            # Broadcast via Redis pub/sub
            try:
                import redis

                from app.config import (
                    REDIS_DB,
                    REDIS_HOST,
                    REDIS_PASSWORD,
                    REDIS_PORT,
                    REDIS_SSL,
                )

                r = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    ssl=REDIS_SSL,
                    decode_responses=True,
                )

                # Broadcast general update for task creation
                message = {
                    "type": "general_update",
                    "data": {"type": "task_created", "task_info": task_info},
                    "timestamp": datetime.now().isoformat(),
                }

                r.publish("general_updates", json.dumps(message))
                logger.info(
                    f"Broadcasted task creation for task {task_id} to all clients"
                )

            except Exception as e:
                logger.error(
                    f"Failed to broadcast task creation for task {task_id}: {str(e)}"
                )

        except Exception as e:
            logger.error(
                f"Error broadcasting task creation for task {task_id}: {str(e)}"
            )
        finally:
            if should_close_db:
                db.close()

    def _create_pipeline_task(
        self, donation_id: int, task_data: Dict[str, Any], db: Optional[Session] = None
    ) -> str:
        """Create a pipeline task in the database."""
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True
        try:
            # Check if a task already exists for this donation
            existing_task = (
                db.query(PipelineTask).filter_by(donation_id=donation_id).first()
            )
            if existing_task:
                logger.info(
                    f"Task already exists for donation {donation_id}: {existing_task.id}, returning existing task"
                )
                return str(existing_task.id)

            # Get the donation to find the subreddit_id
            donation = db.query(Donation).filter(Donation.id == donation_id).first()
            if not donation:
                raise ValueError(f"Donation {donation_id} not found")

            task = PipelineTask(
                type="SUBREDDIT_POST",  # Use 'type' not 'task_type'
                subreddit_id=donation.subreddit_id,
                donation_id=donation_id,
                status=TaskStatus.PENDING.value,
                priority=10,  # Default priority for commission tasks
                context_data=task_data,  # Use 'context_data' not 'task_data'
                created_at=datetime.now(),
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            logger.info(
                f"Created pipeline task {task.id} for donation {donation_id} (user: {donation.customer_name}, tier: {donation.tier})"
            )
            return str(task.id)
        except Exception as e:
            logger.error(
                f"Error creating pipeline task for donation_id={donation_id}: {str(e)}\n{traceback.format_exc()}"
            )
            raise
        finally:
            if should_close_db:
                db.close()

    def _run_commission_task_directly(
        self, task_id: str, donation_id: int, task_data: Dict[str, Any]
    ):
        """
        Run commission task directly in a background thread.

        Args:
            task_id: The task ID
            donation_id: The donation ID
            task_data: Task configuration data
        """

        def run_task():
            try:
                logger.debug(
                    f"Starting commission task {task_id} in background thread (donation_id={donation_id})"
                )

                # Update task status to in progress
                self._update_task_status(task_id, TaskStatus.IN_PROGRESS.value)

                # Create and run the commission worker
                worker = CommissionWorker(donation_id, task_data)

                # Run the async worker in a new event loop
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(worker.run())

                    if success:
                        # Update task status to completed
                        self._update_task_status(task_id, TaskStatus.COMPLETED.value)
                        logger.info(
                            f"Commission task {task_id} completed successfully (donation_id={donation_id})"
                        )
                    else:
                        # Update task status to failed
                        self._update_task_status(
                            task_id,
                            TaskStatus.FAILED.value,
                            "Commission processing failed",
                        )
                        logger.error(
                            f"Commission task {task_id} failed (donation_id={donation_id})"
                        )

                finally:
                    loop.close()

            except Exception as e:
                logger.error(
                    f"Commission task {task_id} failed (donation_id={donation_id}): {str(e)}\n{traceback.format_exc()}"
                )
                # Update task status to failed
                self._update_task_status(task_id, TaskStatus.FAILED.value, str(e))

        # Run the task in a background thread
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        logger.debug(
            f"Commission task {task_id} started in background thread (donation_id={donation_id})"
        )

    def _update_task_status(self, task_id: str, status: str, error_message: str = None):
        """Update task status in the database and broadcast over WebSocket."""
        db = SessionLocal()
        try:
            task = db.query(PipelineTask).filter(PipelineTask.id == task_id).first()
            if task:
                task.status = status

                # Update timing fields
                if status == "in_progress":
                    if hasattr(task, "started_at") and not task.started_at:
                        task.started_at = datetime.now()
                    if hasattr(task, "last_heartbeat"):
                        task.last_heartbeat = datetime.now()
                elif status in ["completed", "failed"]:
                    task.completed_at = datetime.now()

                # Update heartbeat for in_progress tasks
                if status == "in_progress" and hasattr(task, "last_heartbeat"):
                    task.last_heartbeat = datetime.now()

                if error_message:
                    task.error_message = error_message
                db.commit()

                # Handle refund for failed commission tasks
                if status == "failed" and task.donation_id:
                    self._handle_failed_commission_refund(db, task, error_message)

                # Fetch related donation and subreddit for extra info
                donation = task.donation
                subreddit = task.subreddit
                update = {
                    "status": task.status,
                    "completed_at": (
                        task.completed_at.isoformat() if task.completed_at else None
                    ),
                    "error": task.error_message,
                    "reddit_username": (
                        donation.reddit_username
                        if donation
                        and donation.reddit_username
                        and not donation.is_anonymous
                        else "Anonymous"
                    ),
                    "tier": donation.tier if donation else None,
                    "subreddit": subreddit.subreddit_name if subreddit else None,
                    "amount_usd": float(donation.amount_usd) if donation else None,
                    "is_anonymous": donation.is_anonymous if donation else None,
                }
                # Only log major state transitions at INFO level
                if status in ["completed", "failed"]:
                    logger.info(
                        f"Task {task_id} {status}: {donation.customer_name or 'Anonymous'} (${donation.amount_usd})"
                    )
                elif status == "in_progress" and task.status == "pending":
                    logger.info(
                        f"Task {task_id} started: {donation.customer_name or 'Anonymous'} commission"
                    )
                else:
                    logger.debug(f"Task {task_id} status: {status}")
                # Use simple Redis publishing to avoid event loop conflicts
                try:
                    import json

                    import redis

                    from app.config import (
                        REDIS_DB,
                        REDIS_HOST,
                        REDIS_PASSWORD,
                        REDIS_PORT,
                        REDIS_SSL,
                    )

                    # Create a simple Redis client for this operation
                    r = redis.Redis(
                        host=REDIS_HOST,
                        port=REDIS_PORT,
                        db=REDIS_DB,
                        password=REDIS_PASSWORD,
                        ssl=REDIS_SSL,
                        decode_responses=True,
                    )
                    # Create the message
                    message = {
                        "type": "task_update",
                        "task_id": str(task.id),
                        "data": update,
                        "timestamp": datetime.now().isoformat(),
                    }
                    # Publish to Redis
                    r.publish("task_updates", json.dumps(message))
                    # Only log Redis publishing for major status changes or if debug enabled
                    if status in ["completed", "failed"] or logger.isEnabledFor(
                        logging.DEBUG
                    ):
                        logger.debug(f"Published update for task {task.id}: {status}")
                except Exception as e:
                    logger.error(
                        f"[TASK MANAGER] Failed to publish task update for task_id={task_id}: {str(e)}\n{traceback.format_exc()}"
                    )
        except Exception as e:
            logger.error(
                f"Failed to update task status for task_id={task_id}: {str(e)}\n{traceback.format_exc()}"
            )
        finally:
            db.close()

    def _handle_failed_commission_refund(
        self, db: Session, task: PipelineTask, error_message: str
    ):
        """Handle refund for failed commission tasks."""
        try:
            donation = task.donation
            if not donation:
                logger.warning(f"No donation found for failed task {task.id}")
                return

            # Only refund if this is a commission donation with a Stripe payment
            if (
                donation.donation_type != "commission"
                or not donation.stripe_payment_intent_id
            ):
                logger.info(
                    f"Skipping refund for non-commission or manual donation {donation.id}"
                )
                return

            # Only refund if donation was successful (not already failed/refunded)
            if donation.status != "succeeded":
                logger.info(
                    f"Skipping refund for donation {donation.id} with status {donation.status}"
                )
                return

            # Process refund
            from app.services.stripe_service import StripeService

            stripe_service = StripeService()

            refund_reason = (
                f"Commission failed: {error_message}"
                if error_message
                else "Commission processing failed"
            )
            refund_result = stripe_service.refund_payment_intent(
                db, donation.stripe_payment_intent_id, refund_reason
            )

            if refund_result:
                logger.info(
                    f"Successfully refunded commission task {task.id} for donation {donation.id} "
                    f"(amount: ${refund_result['amount_refunded']}, customer: {refund_result['customer_email']})"
                )
            else:
                logger.error(
                    f"Failed to refund commission task {task.id} for donation {donation.id}"
                )

        except Exception as e:
            logger.error(
                f"Error handling refund for failed commission task {task.id}: {str(e)}\n{traceback.format_exc()}"
            )

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status from the database."""
        db = SessionLocal()
        try:
            task = db.query(PipelineTask).filter(PipelineTask.id == task_id).first()
            if task:
                # Get donation information
                donation = task.donation
                subreddit = task.subreddit

                # Calculate progress based on status
                progress = 0
                stage = "pending"
                message = "Task created"

                if task.status == "in_progress":
                    progress = 10
                    stage = "post_fetching"
                    message = "Processing commission..."
                elif task.status == "completed":
                    progress = 100
                    stage = "commission_complete"
                    message = "Commission completed successfully"
                elif task.status == "failed":
                    progress = 0
                    stage = "failed"
                    message = (
                        f"Commission failed: {task.error_message or 'Unknown error'}"
                    )

                return {
                    "task_id": str(task.id),
                    "status": task.status,
                    "created_at": (
                        task.created_at.isoformat() if task.created_at else None
                    ),
                    "completed_at": (
                        task.completed_at.isoformat() if task.completed_at else None
                    ),
                    "error_message": task.error_message,
                    "donation_id": task.donation_id,
                    "stage": stage,
                    "message": message,
                    "progress": progress,
                    "reddit_username": (
                        donation.reddit_username
                        if donation
                        and donation.reddit_username
                        and not donation.is_anonymous
                        else "Anonymous"
                    ),
                    "tier": donation.tier if donation else None,
                    "subreddit": subreddit.subreddit_name if subreddit else None,
                    "amount_usd": float(donation.amount_usd) if donation else None,
                    "is_anonymous": donation.is_anonymous if donation else None,
                    "timestamp": (
                        task.created_at.timestamp() if task.created_at else None
                    ),
                    "started_at": (
                        getattr(task, "started_at", None).isoformat()
                        if hasattr(task, "started_at") and getattr(task, "started_at")
                        else None
                    ),
                    "last_heartbeat": (
                        getattr(task, "last_heartbeat", None).isoformat()
                        if hasattr(task, "last_heartbeat")
                        and getattr(task, "last_heartbeat")
                        else None
                    ),
                    "retry_count": getattr(task, "retry_count", 0),
                    "max_retries": getattr(task, "max_retries", 2),
                    "timeout_seconds": getattr(task, "timeout_seconds", 300),
                }
            return None
        finally:
            db.close()

    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent tasks with donation information."""
        db = SessionLocal()
        try:
            tasks = (
                db.query(PipelineTask)
                .order_by(PipelineTask.created_at.desc())
                .limit(limit)
                .all()
            )
            result = []

            for task in tasks:
                # Get donation information
                donation = task.donation
                subreddit = task.subreddit

                # Calculate progress and stage based on status
                progress = 0
                stage = "pending"
                message = "Task created"

                if task.status == "in_progress":
                    progress = 10
                    stage = "post_fetching"
                    message = "Processing commission..."
                elif task.status == "completed":
                    progress = 100
                    stage = "commission_complete"
                    message = "Commission completed successfully"
                elif task.status == "failed":
                    progress = 0
                    stage = "failed"
                    message = (
                        f"Commission failed: {task.error_message or 'Unknown error'}"
                    )

                task_data = {
                    "task_id": str(task.id),
                    "status": task.status,
                    "created_at": (
                        task.created_at.isoformat() if task.created_at else None
                    ),
                    "completed_at": (
                        task.completed_at.isoformat() if task.completed_at else None
                    ),
                    "donation_id": task.donation_id,
                    "error": task.error_message,
                    "stage": stage,
                    "message": message,
                    "progress": progress,
                    "timestamp": (
                        task.created_at.timestamp() if task.created_at else None
                    ),
                    "started_at": (
                        getattr(task, "started_at", None).isoformat()
                        if hasattr(task, "started_at") and getattr(task, "started_at")
                        else None
                    ),
                    "last_heartbeat": (
                        getattr(task, "last_heartbeat", None).isoformat()
                        if hasattr(task, "last_heartbeat")
                        and getattr(task, "last_heartbeat")
                        else None
                    ),
                    "retry_count": getattr(task, "retry_count", 0),
                    "max_retries": getattr(task, "max_retries", 2),
                    "timeout_seconds": getattr(task, "timeout_seconds", 300),
                }

                # Add donation information if available
                if donation:
                    task_data.update(
                        {
                            "reddit_username": (
                                donation.reddit_username
                                if donation.reddit_username
                                and not donation.is_anonymous
                                else "Anonymous"
                            ),
                            "tier": donation.tier,
                            "amount_usd": float(donation.amount_usd),
                            "is_anonymous": donation.is_anonymous,
                            "commission_message": donation.commission_message,
                        }
                    )

                # Add subreddit information if available
                if subreddit:
                    task_data["subreddit"] = subreddit.subreddit_name

                result.append(task_data)

            return result
        finally:
            db.close()

    def handle_task_failure(self, db: Session, task_id: int, error_message: str):
        """
        Handle task failure and trigger refund if appropriate.

        Args:
            db: Database session
            task_id: ID of the failed task
            error_message: Error message describing the failure
        """
        try:
            # Get the task
            task = db.query(PipelineTask).filter_by(id=task_id).first()
            if not task:
                logger.warning(f"Task {task_id} not found for failure handling")
                return

            # Update task status to failed
            task.status = TaskStatus.FAILED.value
            task.completed_at = datetime.now()
            task.error_message = error_message
            db.commit()

            # Handle refund for failed commission tasks
            if task.donation_id:
                self._handle_failed_commission_refund(db, task, error_message)

            logger.info(f"Handled failure for task {task_id}: {error_message}")

        except Exception as e:
            logger.error(
                f"Error handling task failure for task {task_id}: {str(e)}\n{traceback.format_exc()}"
            )
            db.rollback()

    def update_task_heartbeat(self, task_id: str) -> bool:
        """
        Update the heartbeat for a running task.

        Args:
            task_id: ID of the task to update

        Returns:
            True if updated successfully, False otherwise
        """
        try:
            db = SessionLocal()
            try:
                task = db.query(PipelineTask).filter(PipelineTask.id == task_id).first()
                if task and task.status == "in_progress":
                    if hasattr(task, "last_heartbeat"):
                        task.last_heartbeat = datetime.now()
                        db.commit()
                        logger.debug(f"Updated heartbeat for task {task_id}")
                        return True
                    else:
                        logger.warning(
                            f"Task {task_id} does not have heartbeat support"
                        )
                        return False
                else:
                    logger.warning(f"Task {task_id} not found or not in progress")
                    return False
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error updating heartbeat for task {task_id}: {e}")
            return False
