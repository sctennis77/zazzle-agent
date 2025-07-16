"""
Tests for the task monitor functionality.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.db.models import PipelineTask
from app.services.task_monitor import TaskMonitor
from app.task_manager import TaskManager


class MockTask:
    """Mock task for testing."""

    def __init__(
        self,
        task_id,
        status,
        created_at=None,
        started_at=None,
        last_heartbeat=None,
        retry_count=0,
        max_retries=2,
        timeout_seconds=300,
        donation_id=None,
    ):
        self.id = task_id
        self.status = status
        self.created_at = created_at or datetime.now(timezone.utc)
        self.started_at = started_at
        self.last_heartbeat = last_heartbeat
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.donation_id = donation_id
        self.error_message = None
        self.completed_at = None


@pytest.fixture
def mock_task_manager():
    """Create a mock task manager."""
    return Mock(spec=TaskManager)


@pytest.fixture
def task_monitor(mock_task_manager):
    """Create a task monitor instance."""
    return TaskMonitor(mock_task_manager)


@pytest.mark.asyncio
async def test_task_monitor_initialization(task_monitor):
    """Test task monitor initialization."""
    assert not task_monitor.monitoring
    assert task_monitor.check_interval == 60
    assert task_monitor.task_timeout == 300


@pytest.mark.asyncio
async def test_start_stop_monitoring(task_monitor):
    """Test starting and stopping monitoring."""
    # Start monitoring
    await task_monitor.start_monitoring()
    assert task_monitor.monitoring
    assert task_monitor.monitor_task is not None

    # Stop monitoring
    await task_monitor.stop_monitoring()
    assert not task_monitor.monitoring


@pytest.mark.asyncio
async def test_find_stuck_tasks_no_heartbeat(task_monitor):
    """Test finding stuck tasks with no heartbeat."""
    # Create a mock database session
    mock_db = Mock()

    # Create a task that started 10 minutes ago with no heartbeat
    old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    stuck_task = MockTask(
        task_id=1,
        status="in_progress",
        started_at=old_time,
        last_heartbeat=None,
        timeout_seconds=300,  # 5 minutes
    )

    # Mock the database query
    mock_db.query.return_value.filter.return_value.all.return_value = [stuck_task]

    # Find stuck tasks
    stuck_tasks = task_monitor._find_stuck_tasks(mock_db)

    # Should find the stuck task
    assert len(stuck_tasks) == 1
    assert stuck_tasks[0].id == 1


@pytest.mark.asyncio
async def test_find_stuck_tasks_old_heartbeat(task_monitor):
    """Test finding stuck tasks with old heartbeat."""
    # Create a mock database session
    mock_db = Mock()

    # Create a task with old heartbeat
    old_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=10)
    stuck_task = MockTask(
        task_id=1,
        status="in_progress",
        last_heartbeat=old_heartbeat,
        timeout_seconds=300,  # 5 minutes
    )

    # Mock the database query
    mock_db.query.return_value.filter.return_value.all.return_value = [stuck_task]

    # Find stuck tasks
    stuck_tasks = task_monitor._find_stuck_tasks(mock_db)

    # Should find the stuck task
    assert len(stuck_tasks) == 1
    assert stuck_tasks[0].id == 1


@pytest.mark.asyncio
async def test_find_stuck_tasks_recent_heartbeat(task_monitor):
    """Test that tasks with recent heartbeat are not considered stuck."""
    # Create a mock database session
    mock_db = Mock()

    # Create a task with recent heartbeat
    recent_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=2)
    healthy_task = MockTask(
        task_id=1,
        status="in_progress",
        last_heartbeat=recent_heartbeat,
        timeout_seconds=300,  # 5 minutes
    )

    # Mock the database query
    mock_db.query.return_value.filter.return_value.all.return_value = [healthy_task]

    # Find stuck tasks
    stuck_tasks = task_monitor._find_stuck_tasks(mock_db)

    # Should not find any stuck tasks
    assert len(stuck_tasks) == 0


@pytest.mark.asyncio
async def test_handle_stuck_task_retry(task_monitor):
    """Test handling stuck task with retry."""
    # Create a mock database session
    mock_db = Mock()

    # Create a stuck task that can be retried
    stuck_task = MockTask(
        task_id=1, status="in_progress", retry_count=0, max_retries=2, donation_id=123
    )

    # Mock the restart task method
    task_monitor._restart_task = AsyncMock()

    # Handle the stuck task
    await task_monitor._handle_stuck_task(mock_db, stuck_task)

    # Check that task was reset
    assert stuck_task.status == "pending"
    assert stuck_task.retry_count == 1
    assert stuck_task.started_at is None
    assert stuck_task.last_heartbeat is None

    # Check that restart was called
    task_monitor._restart_task.assert_called_once_with(stuck_task)


@pytest.mark.asyncio
async def test_handle_stuck_task_max_retries(task_monitor):
    """Test handling stuck task that exceeded max retries."""
    # Create a mock database session
    mock_db = Mock()

    # Create a stuck task that exceeded max retries
    stuck_task = MockTask(
        task_id=1, status="in_progress", retry_count=2, max_retries=2, donation_id=123
    )

    # Mock the mark failed method
    task_monitor._mark_task_failed = AsyncMock()

    # Handle the stuck task
    await task_monitor._handle_stuck_task(mock_db, stuck_task)

    # Check that task was marked as failed
    task_monitor._mark_task_failed.assert_called_once_with(
        mock_db, stuck_task, "Task stuck and exceeded max retries"
    )


@pytest.mark.asyncio
async def test_restart_task_with_donation(task_monitor):
    """Test restarting a task with donation ID."""
    # Create a task with donation
    task = MockTask(task_id=1, status="pending", donation_id=123)
    task.context_data = {"some": "data"}

    # Mock the task manager
    task_monitor.task_manager.create_commission_task = Mock()

    # Restart the task
    await task_monitor._restart_task(task)

    # Check that commission task was created
    task_monitor.task_manager.create_commission_task.assert_called_once_with(
        123, {"some": "data"}
    )


@pytest.mark.asyncio
async def test_restart_task_without_donation(task_monitor, caplog):
    """Test restarting a task without donation ID."""
    # Create a task without donation
    task = MockTask(task_id=1, status="pending", donation_id=None)

    # Restart the task
    await task_monitor._restart_task(task)

    # Check that warning was logged
    assert "cannot restart automatically" in caplog.text


@pytest.mark.asyncio
async def test_get_monitoring_status(task_monitor):
    """Test getting monitoring status."""
    status = task_monitor.get_monitoring_status()

    assert "monitoring" in status
    assert "check_interval" in status
    assert "task_timeout" in status
    assert "monitor_task_running" in status


@pytest.mark.asyncio
async def test_check_stuck_tasks_once(task_monitor):
    """Test one-time stuck task check."""
    # Mock the database
    with patch("app.services.task_monitor.SessionLocal") as mock_session:
        mock_db = Mock()
        mock_session.return_value = mock_db

        # Create a stuck task
        stuck_task = MockTask(task_id=1, status="in_progress", donation_id=123)

        # Mock the find stuck tasks method
        task_monitor._find_stuck_tasks = Mock(return_value=[stuck_task])

        # Check stuck tasks
        result = await task_monitor.check_stuck_tasks_once()

        # Check result
        assert result["stuck_tasks_found"] == 1
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["task_id"] == 1
        assert result["tasks"][0]["donation_id"] == 123


if __name__ == "__main__":
    pytest.main([__file__])
