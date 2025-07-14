"""
Unified Task Manager for commission processing.

This module provides a unified interface for task management that can use
both Kubernetes Jobs and direct execution as fallback
"""

import json
import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import asyncio
import traceback

from app.db.database import SessionLocal
from sqlalchemy.orm import Session
from app.db.models import Donation, PipelineTask
from app.k8s_job_manager import K8sJobManager
from app.commission_worker import CommissionWorker
from app.utils.logging_config import get_logger

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
        self.k8s_manager = K8sJobManager()
        self.use_k8s = self.k8s_manager.enabled
        logger.info(f"Task Manager initialized - K8s available: {self.use_k8s}")
    
    def create_commission_task(self, donation_id: int, task_data: Dict[str, Any], db: Optional[Session] = None) -> str:
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
        
        if self.use_k8s:
            # Use Kubernetes Jobs
            logger.info(f"Creating K8s Job for task {task_id} (donation_id={donation_id})")
            self.k8s_manager.create_commission_job(task_id, donation_id, task_data)
        else:
            # Use direct execution fallback
            logger.info(f"Running commission task {task_id} directly (donation_id={donation_id})")
            self._run_commission_task_directly(task_id, donation_id, task_data)
        
        return task_id
    
    def _create_pipeline_task(self, donation_id: int, task_data: Dict[str, Any], db: Optional[Session] = None) -> str:
        """Create a pipeline task in the database."""
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True
        try:
            # Check if a task already exists for this donation
            existing_task = db.query(PipelineTask).filter_by(donation_id=donation_id).first()
            if existing_task:
                logger.info(f"Task already exists for donation {donation_id}: {existing_task.id}, returning existing task")
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
                created_at=datetime.now()
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            logger.info(f"Created pipeline task {task.id} for donation {donation_id} (user: {donation.customer_name}, tier: {donation.tier})")
            return str(task.id)
        except Exception as e:
            logger.error(f"Error creating pipeline task for donation_id={donation_id}: {str(e)}\n{traceback.format_exc()}")
            raise
        finally:
            if should_close_db:
                db.close()
    
    def _run_commission_task_directly(self, task_id: str, donation_id: int, task_data: Dict[str, Any]):
        """
        Run commission task directly in a background thread.
        
        Args:
            task_id: The task ID
            donation_id: The donation ID
            task_data: Task configuration data
        """
        def run_task():
            try:
                logger.debug(f"Starting commission task {task_id} in background thread (donation_id={donation_id})")
                
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
                        logger.info(f"Commission task {task_id} completed successfully (donation_id={donation_id})")
                    else:
                        # Update task status to failed
                        self._update_task_status(task_id, TaskStatus.FAILED.value, "Commission processing failed")
                        logger.error(f"Commission task {task_id} failed (donation_id={donation_id})")
                        
                finally:
                    loop.close()
                
            except Exception as e:
                logger.error(f"Commission task {task_id} failed (donation_id={donation_id}): {str(e)}\n{traceback.format_exc()}")
                # Update task status to failed
                self._update_task_status(task_id, TaskStatus.FAILED.value, str(e))
        
        # Run the task in a background thread
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        logger.debug(f"Commission task {task_id} started in background thread (donation_id={donation_id})")
    
    def _update_task_status(self, task_id: str, status: str, error_message: str = None):
        """Update task status in the database and broadcast over WebSocket."""
        db = SessionLocal()
        try:
            task = db.query(PipelineTask).filter(PipelineTask.id == task_id).first()
            if task:
                task.status = status
                if status in ["completed", "failed"]:
                    task.completed_at = datetime.now()
                if error_message:
                    task.error_message = error_message
                db.commit()
                # Fetch related donation and subreddit for extra info
                donation = task.donation
                subreddit = task.subreddit
                update = {
                    "status": task.status,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "error": task.error_message,
                    "reddit_username": donation.reddit_username if donation and donation.reddit_username and not donation.is_anonymous else "Anonymous",
                    "tier": donation.tier if donation else None,
                    "subreddit": subreddit.subreddit_name if subreddit else None,
                    "amount_usd": float(donation.amount_usd) if donation else None,
                    "is_anonymous": donation.is_anonymous if donation else None,
                }
                # Log every status update at INFO level, with context
                logger.info(f"Task {task_id} status updated to {status} (donation_id={task.donation_id}, user: {donation.customer_name if donation else 'Unknown'})")
                # Use simple Redis publishing to avoid event loop conflicts
                try:
                    import redis
                    import json
                    from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB
                    # Create a simple Redis client for this operation
                    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
                    # Create the message
                    message = {
                        "type": "task_update",
                        "task_id": str(task.id),
                        "data": update,
                        "timestamp": datetime.now().isoformat()
                    }
                    # Publish to Redis
                    r.publish("task_updates", json.dumps(message))
                    logger.debug(f"[TASK MANAGER] Published task update for {task.id}: {update}")
                except Exception as e:
                    logger.error(f"[TASK MANAGER] Failed to publish task update for task_id={task_id}: {str(e)}\n{traceback.format_exc()}")
        except Exception as e:
            logger.error(f"Failed to update task status for task_id={task_id}: {str(e)}\n{traceback.format_exc()}")
        finally:
            db.close()
    
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
                    message = f"Commission failed: {task.error_message or 'Unknown error'}"
                
                return {
                    "task_id": str(task.id),
                    "status": task.status,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "error_message": task.error_message,
                    "donation_id": task.donation_id,
                    "stage": stage,
                    "message": message,
                    "progress": progress,
                    "reddit_username": donation.reddit_username if donation and donation.reddit_username and not donation.is_anonymous else "Anonymous",
                    "tier": donation.tier if donation else None,
                    "subreddit": subreddit.subreddit_name if subreddit else None,
                    "amount_usd": float(donation.amount_usd) if donation else None,
                    "is_anonymous": donation.is_anonymous if donation else None,
                    "timestamp": task.created_at.timestamp() if task.created_at else None
                }
            return None
        finally:
            db.close()
    
    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent tasks with donation information."""
        db = SessionLocal()
        try:
            tasks = db.query(PipelineTask).order_by(PipelineTask.created_at.desc()).limit(limit).all()
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
                    message = f"Commission failed: {task.error_message or 'Unknown error'}"
                
                task_data = {
                    "task_id": str(task.id),
                    "status": task.status,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "donation_id": task.donation_id,
                    "error": task.error_message,
                    "stage": stage,
                    "message": message,
                    "progress": progress,
                    "timestamp": task.created_at.timestamp() if task.created_at else None
                }
                
                # Add donation information if available
                if donation:
                    task_data.update({
                        "reddit_username": donation.reddit_username if donation.reddit_username and not donation.is_anonymous else "Anonymous",
                        "tier": donation.tier,
                        "amount_usd": float(donation.amount_usd),
                        "is_anonymous": donation.is_anonymous,
                        "commission_message": donation.commission_message,
                    })
                
                # Add subreddit information if available
                if subreddit:
                    task_data["subreddit"] = subreddit.subreddit_name
                
                result.append(task_data)
            
            return result
        finally:
            db.close() 