# Task Status Progress Logging Cleanup Proposal

## Current Issues

### 1. **Excessive Image Generation Progress Logging** (reddit_agent.py:556-620)
- **Problem**: 15+ INFO logs per commission with verbose formatting
- **Current Noise Level**: High - every 0.5-1.5 seconds during image generation

### 2. **Duplicate Task Status Updates** (task_manager.py:188, commission_worker.py:214)
- **Problem**: Same status changes logged in multiple locations
- **Current Noise Level**: Medium - INFO for all state changes

### 3. **Redundant Redis Publishing** (task_manager.py:205, commission_worker.py:240)
- **Problem**: Multiple DEBUG logs for same publishing operation
- **Current Noise Level**: Medium - DEBUG but creates development noise

## Proposed Changes

### Priority 1: Reduce Image Generation Progress Noise

**File: `app/agents/reddit_agent.py`**

```python
# BEFORE (lines 556-620): 15+ INFO logs
logger.info(f"=== _send_image_generation_progress START ===")
logger.info(f"Progress update {i+1}/{total_updates}: {current_progress}%")
logger.info(f"Successfully sent progress callback for {current_progress}%")

# AFTER: Consolidate to key milestones only
async def _send_image_generation_progress(self, delay: int = 1, image_title: str = None):
    """Send key progress milestones during image generation."""
    try:
        logger.debug("Starting image generation progress updates")
        await asyncio.sleep(delay)
        
        # Only log key milestones: start, 25%, 50%, 75%, 90%
        milestones = [40, 55, 70, 85, 89]
        
        for i, progress in enumerate(milestones):
            if self.progress_callback:
                try:
                    await self.progress_callback("image_generation_progress", {"progress": progress})
                    if progress in [40, 89]:  # Only log start and end
                        logger.info(f"Image generation progress: {progress}%")
                except Exception as e:
                    logger.error(f"Progress callback failed at {progress}%: {e}")
            
            if i < len(milestones) - 1:
                await asyncio.sleep(random.uniform(2.0, 3.0))  # Longer intervals
                
        # Simplified event coordination
        if hasattr(self, 'image_generation_event') and self.image_generation_event:
            await self.image_generation_event.wait()
            
    except asyncio.CancelledError:
        logger.debug("Progress updates cancelled")
        raise
    except Exception as e:
        logger.error(f"Progress update error: {e}")
```

### Priority 2: Consolidate Task Status Logging

**File: `app/task_manager.py`**

```python
# BEFORE (line 188): Log all status changes at INFO
logger.info(f"Task {task_id} status updated to {status} (donation_id={task.donation_id}, user: {donation.customer_name if donation else 'Unknown'})")

# AFTER: Only log significant state changes at INFO
def _update_task_status(self, task_id: str, status: str, error_message: str = None):
    # ... existing code ...
    
    # Only log major state transitions at INFO level
    if status in ["completed", "failed"]:
        logger.info(f"Task {task_id} {status}: {donation.customer_name or 'Anonymous'} (${donation.amount_usd})")
    elif status == "in_progress" and task.status == "pending":
        logger.info(f"Task {task_id} started: {donation.customer_name or 'Anonymous'} commission")
    else:
        logger.debug(f"Task {task_id} status: {status}")
```

**File: `app/commission_worker.py`**

```python
# BEFORE (line 214): Duplicate status logging
logger.debug(f"Updated pipeline task {self.pipeline_task.id} status to {status} (donation_id={self.donation_id})")

# AFTER: Remove duplicate - let TaskManager handle status logging
def _update_task_status(self, status: str, error_message: str = None, progress: int = None, stage: str = None, message: str = None):
    try:
        if not self.pipeline_task:
            logger.warning(f"No pipeline task to update for donation_id={self.donation_id}")
            return
            
        self.pipeline_task.status = status
        if status in ["completed", "failed"]:
            self.pipeline_task.completed_at = datetime.now()
        if error_message:
            self.pipeline_task.error_message = error_message
        self.db.commit()
        
        # Remove duplicate logging - TaskManager handles status logs
        update = self._build_update_dict(status, error_message, progress, stage, message)
        if update:
            self._publish_task_update_simple(self.pipeline_task.id, update)
```

### Priority 3: Consolidate Redis Publishing Logs

**File: `app/task_manager.py` & `app/commission_worker.py`**

```python
# BEFORE: Multiple DEBUG logs with different prefixes
logger.debug(f"[TASK MANAGER] Published task update for {task.id}: {update}")
logger.debug(f"[SIMPLE REDIS] Published task update for {task_id}: {update}")

# AFTER: Single standardized Redis log format
def _publish_task_update_simple(self, task_id: str, update: dict):
    try:
        # ... Redis publishing code ...
        r.publish("task_updates", json.dumps(message))
        
        # Only log Redis publishing for errors or major status changes
        if update.get("status") in ["completed", "failed"] or logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Published update for task {task_id}: {update.get('status', 'unknown')}")
            
    except Exception as e:
        logger.error(f"Failed to publish task update for {task_id}: {e}")
```

### Priority 4: Clean Up WebSocket Event Coordination

**File: `app/agents/reddit_agent.py`**

```python
# BEFORE (lines 607-612): Verbose event coordination
logger.info("Waiting for image generation event to be set")
logger.info("Image generation event received, progress task completing")
logger.warning("No image_generation_event found, proceeding without coordination")

# AFTER: Minimal event coordination logging
if hasattr(self, 'image_generation_event') and self.image_generation_event:
    await self.image_generation_event.wait()
    logger.debug("Image generation completed")
```

## Expected Impact

### Noise Reduction
- **Image Generation**: 15+ INFO logs → 2 INFO logs (start/end)
- **Task Status**: All changes logged → Only major transitions logged
- **Redis Publishing**: Duplicate logs → Single standardized format
- **Event Coordination**: Verbose INFO → Minimal DEBUG

### Information Preserved
- Major state transitions (pending→in_progress, completed, failed)
- User identification and commission amounts
- Error conditions and failure reasons
- Performance milestones (image generation start/end)

### Development Experience
- Cleaner logs during development
- Easier to spot actual issues
- Reduced log volume in production
- Important events still visible

## Implementation Order

1. **Immediate Impact**: Reddit Agent progress logging cleanup
2. **Medium Priority**: Consolidate task status logging
3. **Low Priority**: Redis publishing deduplication
4. **Cleanup**: Remove verbose coordination logging

This approach maintains operational visibility while dramatically reducing log noise during commission processing.