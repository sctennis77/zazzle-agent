import asyncio
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Donation, SchedulerConfig, Subreddit
from app.models import DonationStatus, DonationTier
from app.redis_service import RedisService
from app.services.scheduler_service import SchedulerService
from app.task_manager import TaskManager


class TestSchedulerService(unittest.IsolatedAsyncioTestCase):
    """Test cases for the SchedulerService class."""

    def setUp(self):
        """Set up test database and dependencies."""
        # Create in-memory SQLite database for testing
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        TestSession = sessionmaker(bind=self.engine)
        self.db = TestSession()

        # Mock dependencies
        self.mock_redis_service = Mock(spec=RedisService)
        self.mock_task_manager = Mock(spec=TaskManager)
        
        # Create scheduler service
        self.scheduler_service = SchedulerService(
            self.mock_redis_service, self.mock_task_manager
        )

    def tearDown(self):
        """Clean up test database."""
        self.db.close()

    def test_get_scheduler_status_no_config(self):
        """Test getting scheduler status when no config exists."""
        status = self.scheduler_service.get_scheduler_status(self.db)
        
        expected = {
            "enabled": False,
            "interval_hours": 24,
            "last_run_at": None,
            "next_run_at": None,
        }
        self.assertEqual(status, expected)

    def test_get_scheduler_status_with_config(self):
        """Test getting scheduler status with existing config."""
        # Create scheduler config
        now = datetime.now(timezone.utc)
        config = SchedulerConfig(
            enabled=True,
            interval_hours=12,
            last_run_at=now,
            next_run_at=now + timedelta(hours=12),
        )
        self.db.add(config)
        self.db.commit()

        status = self.scheduler_service.get_scheduler_status(self.db)
        
        self.assertEqual(status["enabled"], True)
        self.assertEqual(status["interval_hours"], 12)
        # Check that the ISO format includes timezone info
        self.assertTrue(status["last_run_at"].endswith("+00:00") or status["last_run_at"].endswith("Z"))
        self.assertTrue(status["next_run_at"].endswith("+00:00") or status["next_run_at"].endswith("Z"))

    def test_update_scheduler_config_new(self):
        """Test updating scheduler config when none exists."""
        config = self.scheduler_service.update_scheduler_config(
            self.db, enabled=True, interval_hours=6
        )
        
        self.assertEqual(config["enabled"], True)
        self.assertEqual(config["interval_hours"], 6)
        self.assertIsNone(config["last_run_at"])
        self.assertIsNone(config["next_run_at"])

    def test_update_scheduler_config_existing(self):
        """Test updating existing scheduler config."""
        # Create initial config
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        existing_config = SchedulerConfig(
            enabled=False,
            interval_hours=24,
            last_run_at=past_time,
            next_run_at=past_time + timedelta(hours=24),
        )
        self.db.add(existing_config)
        self.db.commit()

        # Update config
        config = self.scheduler_service.update_scheduler_config(
            self.db, enabled=True, interval_hours=6
        )
        
        self.assertEqual(config["enabled"], True)
        self.assertEqual(config["interval_hours"], 6)
        # Should recalculate next_run_at based on new interval - check timezone format
        self.assertTrue(config["next_run_at"].endswith("+00:00") or config["next_run_at"].endswith("Z"))

    async def test_should_run_scheduled_commission_disabled(self):
        """Test should_run when scheduler is disabled."""
        config = SchedulerConfig(enabled=False, interval_hours=24)
        self.db.add(config)
        self.db.commit()

        should_run = await self.scheduler_service.should_run_scheduled_commission(self.db)
        self.assertFalse(should_run)

    async def test_should_run_scheduled_commission_no_last_run(self):
        """Test should_run when no last run recorded."""
        config = SchedulerConfig(enabled=True, interval_hours=24, last_run_at=None)
        self.db.add(config)
        self.db.commit()

        should_run = await self.scheduler_service.should_run_scheduled_commission(self.db)
        self.assertTrue(should_run)

    async def test_should_run_scheduled_commission_interval_not_passed(self):
        """Test should_run when interval hasn't passed."""
        # Last run was 1 hour ago, interval is 24 hours
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        config = SchedulerConfig(
            enabled=True, 
            interval_hours=24, 
            last_run_at=recent_time
        )
        self.db.add(config)
        self.db.commit()

        should_run = await self.scheduler_service.should_run_scheduled_commission(self.db)
        self.assertFalse(should_run)

    async def test_should_run_scheduled_commission_interval_passed(self):
        """Test should_run when interval has passed."""
        # Last run was 25 hours ago, interval is 24 hours
        old_time = datetime.now(timezone.utc) - timedelta(hours=25)
        config = SchedulerConfig(
            enabled=True, 
            interval_hours=24, 
            last_run_at=old_time
        )
        self.db.add(config)
        self.db.commit()

        should_run = await self.scheduler_service.should_run_scheduled_commission(self.db)
        self.assertTrue(should_run)

    @patch('app.services.scheduler_service.get_subreddit_service')
    @patch('app.agents.reddit_agent.pick_subreddit')
    @patch('app.services.commission_validator.CommissionValidator')
    @patch('app.agents.reddit_agent.RedditAgent')
    async def test_create_scheduled_commission_success(self, mock_reddit_agent, mock_validator_class, mock_pick_subreddit, mock_get_subreddit_service):
        """Test successful scheduled commission creation."""
        # Setup mocks
        mock_pick_subreddit.return_value = "golf"
        
        # Create test subreddit
        test_subreddit = Subreddit(id=1, subreddit_name="golf")
        self.db.add(test_subreddit)
        self.db.commit()
        
        mock_subreddit_service = Mock()
        mock_subreddit_service.get_or_create_subreddit.return_value = test_subreddit
        mock_get_subreddit_service.return_value = mock_subreddit_service
        
        # Mock validation
        mock_validation_result = Mock()
        mock_validation_result.valid = True
        mock_validation_result.post_id = "test_post_123"
        
        mock_validator = Mock()
        mock_validator.validate_commission = AsyncMock(return_value=mock_validation_result)
        mock_validator_class.return_value = mock_validator
        
        # Mock task manager
        self.mock_task_manager.create_commission_task.return_value = "task_123"
        
        # Call the method
        result = await self.scheduler_service._create_scheduled_commission(self.db)
        
        # Verify result
        self.assertIn("donation_id", result)
        self.assertEqual(result["task_id"], "task_123")
        self.assertEqual(result["subreddit"], "golf")
        self.assertEqual(result["amount_usd"], 1.0)
        self.assertEqual(result["tier"], "bronze")
        self.assertEqual(result["validated_post_id"], "test_post_123")
        
        # Verify donation was created
        donation = self.db.query(Donation).first()
        self.assertIsNotNone(donation)
        self.assertEqual(donation.customer_name, "Clouvel")
        self.assertEqual(donation.amount_usd, 1.0)
        self.assertEqual(donation.tier, DonationTier.BRONZE.value)
        self.assertEqual(donation.commission_type, "random_subreddit")
        self.assertEqual(donation.post_id, "test_post_123")

    @patch('app.agents.reddit_agent.pick_subreddit')
    @patch('app.services.commission_validator.CommissionValidator')
    @patch('app.agents.reddit_agent.RedditAgent')
    async def test_create_scheduled_commission_validation_fails(self, mock_reddit_agent, mock_validator_class, mock_pick_subreddit):
        """Test scheduled commission creation when validation fails."""
        mock_pick_subreddit.return_value = "invalid_subreddit"
        
        # Mock validation failure
        mock_validation_result = Mock()
        mock_validation_result.valid = False
        mock_validation_result.error = "Subreddit not found"
        
        mock_validator = Mock()
        mock_validator.validate_commission = AsyncMock(return_value=mock_validation_result)
        mock_validator_class.return_value = mock_validator
        
        # Should raise exception
        with self.assertRaises(Exception) as context:
            await self.scheduler_service._create_scheduled_commission(self.db)
        
        self.assertIn("Commission validation failed", str(context.exception))

    async def test_run_scheduled_commission_lock_not_acquired(self):
        """Test run_scheduled_commission when lock cannot be acquired."""
        # Mock lock acquisition failure
        self.mock_redis_service.acquire_lock = AsyncMock(return_value=False)
        
        result = await self.scheduler_service.run_scheduled_commission(self.db)
        
        self.assertIsNone(result)
        self.mock_redis_service.acquire_lock.assert_called_once()

    async def test_run_scheduled_commission_should_not_run(self):
        """Test run_scheduled_commission when should_run returns False."""
        # Mock lock acquisition success
        self.mock_redis_service.acquire_lock = AsyncMock(return_value=True)
        self.mock_redis_service.release_lock = AsyncMock(return_value=True)
        
        # Create config that says we shouldn't run
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        config = SchedulerConfig(
            enabled=True, 
            interval_hours=24, 
            last_run_at=recent_time
        )
        self.db.add(config)
        self.db.commit()
        
        result = await self.scheduler_service.run_scheduled_commission(self.db)
        
        self.assertIsNone(result)
        self.mock_redis_service.release_lock.assert_called_once()

    def test_update_scheduler_last_run_new_config(self):
        """Test updating last run time creates new config if none exists."""
        # Ensure no config exists
        self.assertEqual(self.db.query(SchedulerConfig).count(), 0)
        
        self.scheduler_service._update_scheduler_last_run(self.db)
        
        # Should create new config
        config = self.db.query(SchedulerConfig).first()
        self.assertIsNotNone(config)
        self.assertTrue(config.enabled)
        self.assertEqual(config.interval_hours, 24)
        self.assertIsNotNone(config.last_run_at)
        self.assertIsNotNone(config.next_run_at)

    def test_update_scheduler_last_run_existing_config(self):
        """Test updating last run time with existing config."""
        # Create existing config
        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        config = SchedulerConfig(
            enabled=True,
            interval_hours=12,
            last_run_at=old_time,
            next_run_at=old_time + timedelta(hours=12),
        )
        self.db.add(config)
        self.db.commit()
        
        self.scheduler_service._update_scheduler_last_run(self.db)
        
        # Refresh config
        self.db.refresh(config)
        
        # Should update times but preserve other settings
        self.assertTrue(config.enabled)
        self.assertEqual(config.interval_hours, 12)
        # Compare timestamps - ensure both are timezone-aware
        if config.last_run_at.tzinfo is None:
            config_last_run = config.last_run_at.replace(tzinfo=timezone.utc)
        else:
            config_last_run = config.last_run_at
        self.assertGreater(config_last_run, old_time)
        self.assertIsNotNone(config.next_run_at)


if __name__ == "__main__":
    unittest.main()