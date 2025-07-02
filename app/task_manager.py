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

from app.db.database import SessionLocal
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
    
    def create_commission_task(self, donation_id: int, task_data: Dict[str, Any]) -> str:
        """
        Create a commission task using either K8s Jobs or direct execution.
        
        Args:
            donation_id: The donation ID
            task_data: Task configuration data
            
        Returns:
            Task ID
        """
        # Create the pipeline task in the database
        task_id = self._create_pipeline_task(donation_id, task_data)
        
        if self.use_k8s:
            # Use Kubernetes Jobs
            logger.info(f"Creating K8s Job for task {task_id}")
            self.k8s_manager.create_commission_job(task_id, donation_id, task_data)
        else:
            # Use direct execution fallback
            logger.info(f"Running commission task {task_id} directly")
            self._run_commission_task_directly(task_id, donation_id, task_data)
        
        return task_id
    
    def _create_pipeline_task(self, donation_id: int, task_data: Dict[str, Any]) -> str:
        """Create a pipeline task in the database."""
        db = SessionLocal()
        try:
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
            return str(task.id)
        finally:
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
                logger.info(f"Starting commission task {task_id} in background thread")
                
                # Update task status to in progress
                self._update_task_status(task_id, TaskStatus.IN_PROGRESS.value)
                
                # Create and run the commission worker
                worker = CommissionWorker(donation_id, task_data)
                import asyncio
                
                # Run the async worker in a new event loop
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(worker.run())
                    
                    if success:
                        # Update task status to completed
                        self._update_task_status(task_id, TaskStatus.COMPLETED.value)
                        logger.info(f"Commission task {task_id} completed successfully")
                    else:
                        # Update task status to failed
                        self._update_task_status(task_id, TaskStatus.FAILED.value, "Commission processing failed")
                        logger.error(f"Commission task {task_id} failed")
                        
                finally:
                    loop.close()
                
            except Exception as e:
                logger.error(f"Commission task {task_id} failed: {e}")
                # Update task status to failed
                self._update_task_status(task_id, TaskStatus.FAILED.value, str(e))
        
        # Run the task in a background thread
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        logger.info(f"Commission task {task_id} started in background thread")
    
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
                import asyncio
                from app.redis_service import redis_service
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(redis_service.publish_task_update(str(task.id), update))
                    else:
                        loop.run_until_complete(redis_service.publish_task_update(str(task.id), update))
                except RuntimeError:
                    # If no event loop, create one
                    asyncio.run(redis_service.publish_task_update(str(task.id), update))
                except Exception as e:
                    logger.error(f"Failed to publish task update to Redis: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
        finally:
            db.close()
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status from the database."""
        db = SessionLocal()
        try:
            task = db.query(PipelineTask).filter(PipelineTask.id == task_id).first()
            if task:
                return {
                    "task_id": str(task.id),
                    "status": task.status,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "error_message": task.error_message,
                    "donation_id": task.donation_id
                }
            return None
        finally:
            db.close()
    
    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent tasks."""
        db = SessionLocal()
        try:
            tasks = db.query(PipelineTask).order_by(PipelineTask.created_at.desc()).limit(limit).all()
            return [
                {
                    "task_id": str(task.id),
                    "status": task.status,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "donation_id": task.donation_id
                }
                for task in tasks
            ]
        finally:
            db.close() 