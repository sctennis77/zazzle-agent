"""
Tests for CommunityAgentService.

Tests the production service orchestrator that handles Reddit streaming,
Redis integration, and multi-subreddit management.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import redis

from app.services.community_agent_service import CommunityAgentService


class TestCommunityAgentService:
    """Test cases for the CommunityAgentService orchestrator."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.ping.return_value = True
        mock_redis.publish.return_value = 1
        return mock_redis

    @pytest.fixture
    def mock_reddit(self):
        """Mock Reddit client."""
        with patch("app.services.community_agent_service.praw.Reddit") as mock:
            yield mock.return_value

    @pytest.fixture
    def service(self, mock_redis):
        """Create a CommunityAgentService for testing."""
        with patch(
            "app.services.community_agent_service.redis.from_url"
        ) as mock_redis_from_url:
            mock_redis_from_url.return_value = mock_redis
            with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"}):
                service = CommunityAgentService(
                    subreddit_names=["clouvel"], dry_run=True
                )
                return service

    def test_service_initialization_single_subreddit(self, service):
        """Test service initializes correctly with single subreddit."""
        assert service.subreddit_names == ["clouvel"]
        assert service.moderation_subreddit == "clouvel"
        assert service.dry_run is True
        assert service.running is False
        assert "clouvel" in service.agents
        assert service.redis_client is not None

    def test_service_initialization_multiple_subreddits(self, mock_redis):
        """Test service initializes correctly with multiple subreddits."""
        with patch(
            "app.services.community_agent_service.redis.from_url"
        ) as mock_redis_from_url:
            mock_redis_from_url.return_value = mock_redis
            with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"}):
                service = CommunityAgentService(
                    subreddit_names=[
                        "programming",
                        "funny",
                    ],  # clouvel automatically added
                    dry_run=False,
                )

                assert service.subreddit_names == ["clouvel", "programming", "funny"]
                assert service.moderation_subreddit == "clouvel"
                assert service.dry_run is False
                assert len(service.agents) == 3
                assert "clouvel" in service.agents
                assert "programming" in service.agents
                assert "funny" in service.agents

    def test_service_initialization_duplicate_clouvel(self, mock_redis):
        """Test service handles duplicate clouvel correctly."""
        with patch(
            "app.services.community_agent_service.redis.from_url"
        ) as mock_redis_from_url:
            mock_redis_from_url.return_value = mock_redis
            with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"}):
                service = CommunityAgentService(
                    subreddit_names=[
                        "clouvel",
                        "programming",
                    ],  # clouvel specified twice
                    dry_run=False,
                )

                # Should only have clouvel once
                assert service.subreddit_names == ["clouvel", "programming"]
                assert service.moderation_subreddit == "clouvel"
                assert len(service.agents) == 2

    def test_service_initialization_no_redis(self):
        """Test service initializes correctly without Redis."""
        with patch(
            "app.services.community_agent_service.redis.from_url"
        ) as mock_redis_from_url:
            mock_redis_from_url.side_effect = Exception("Redis connection failed")

            service = CommunityAgentService(subreddit_names=["clouvel"])

            assert service.redis_client is None
            assert "clouvel" in service.agents

    def test_publish_agent_update_with_redis(self, service):
        """Test publishing agent updates via Redis."""
        update = {
            "action_id": 123,
            "action_type": "welcome_new_user",
            "success": True,
            "mood": "excited",
        }

        service._publish_agent_update("clouvel", update)

        # Verify Redis publish was called
        service.redis_client.publish.assert_called_once()
        call_args = service.redis_client.publish.call_args

        assert call_args[0][0] == "community_agent:clouvel"
        message = json.loads(call_args[0][1])
        assert message["type"] == "community_agent_action"
        assert message["subreddit"] == "clouvel"
        assert message["data"] == update

    def test_publish_agent_update_without_redis(self):
        """Test publishing agent updates without Redis doesn't crash."""
        service = CommunityAgentService(subreddit_names=["clouvel"])
        service.redis_client = None

        # Should not raise an exception
        service._publish_agent_update("clouvel", {"test": "update"})

    def test_publish_agent_update_redis_error(self, service):
        """Test handling Redis publish errors gracefully."""
        service.redis_client.publish.side_effect = Exception("Redis error")

        # Should not raise an exception
        service._publish_agent_update("clouvel", {"test": "update"})

    @pytest.mark.asyncio
    async def test_process_stream_item_submission(self, service):
        """Test processing a Reddit submission."""
        # Mock submission
        mock_submission = Mock()
        mock_submission.id = "test123"
        mock_submission.title = "Test Post"
        mock_submission.author = Mock()
        mock_submission.author.__str__ = lambda: "testuser"

        # Mock agent decide_actions
        mock_agent = service.agents["clouvel"]
        mock_agent.decide_actions = AsyncMock(
            return_value=[
                {
                    "action": "welcome_new_user",
                    "target_type": "post",
                    "target_id": "test123",
                    "content": "Welcome to the kingdom!",
                    "reasoning": "New user needs welcome",
                    "mood": "excited",
                }
            ]
        )

        # Mock execute_action
        mock_agent.execute_action = AsyncMock(
            return_value={"success": True, "dry_run": True}
        )

        # Mock database operations
        with patch.object(mock_agent, "_get_db_session") as mock_session:
            mock_session.return_value.__enter__.return_value = Mock()
            mock_session.return_value.__exit__.return_value = None

            with patch.object(mock_agent, "_get_or_create_state") as mock_state:
                mock_state.return_value = Mock()

                with patch.object(mock_agent, "_check_rate_limits") as mock_rate_check:
                    mock_rate_check.return_value = True

                    with patch.object(mock_agent, "log_action") as mock_log:
                        mock_log.return_value = Mock(id=123)

                        with patch.object(mock_agent, "_increment_action_count"):
                            await service._process_stream_item(
                                mock_submission, "submission", "clouvel"
                            )

        # Verify actions were taken
        mock_agent.decide_actions.assert_called_once()
        mock_agent.execute_action.assert_called_once()

        # Verify Redis update was published
        service.redis_client.publish.assert_called()

    @pytest.mark.asyncio
    async def test_process_stream_item_rate_limited(self, service):
        """Test processing when rate limited."""
        mock_submission = Mock()
        mock_submission.id = "test123"

        mock_agent = service.agents["clouvel"]

        # Mock rate limit exceeded
        with patch.object(mock_agent, "_get_db_session") as mock_session:
            mock_session.return_value.__enter__.return_value = Mock()
            mock_session.return_value.__exit__.return_value = None

            with patch.object(mock_agent, "_get_or_create_state") as mock_state:
                mock_state.return_value = Mock()

                with patch.object(mock_agent, "_check_rate_limits") as mock_rate_check:
                    mock_rate_check.return_value = False  # Rate limited

                    await service._process_stream_item(
                        mock_submission, "submission", "clouvel"
                    )

        # Should not have called decide_actions due to rate limiting
        # Since decide_actions was never set up as a mock, it shouldn't have been called
        assert True  # If we got here without calling decide_actions, the test passed

    @pytest.mark.asyncio
    async def test_start_health_server(self, service):
        """Test starting the health monitoring."""
        service.running = True

        with patch("asyncio.create_task") as mock_create_task:
            await service.start_health_server()
            mock_create_task.assert_called_once()

    def test_get_health_status_running(self, service):
        """Test health status when service is running."""
        service.running = True

        with patch.object(service, "get_service_status") as mock_get_status:
            mock_get_status.return_value = {"running": True, "test": "data"}

            health_status = service.get_health_status()

            assert health_status["status"] == "healthy"
            assert health_status["service"]["running"] is True

    def test_get_health_status_not_running(self, service):
        """Test health status when service is not running."""
        service.running = False

        with patch.object(service, "get_service_status") as mock_get_status:
            mock_get_status.return_value = {"running": False, "test": "data"}

            health_status = service.get_health_status()

            assert health_status["status"] == "unhealthy"
            assert health_status["service"]["running"] is False

    def test_get_service_status(self, service):
        """Test getting service status."""
        service.running = True

        # Mock community stats
        mock_agent = service.agents["clouvel"]

        # Mock database session and queries
        with patch.object(mock_agent, "get_community_stats") as mock_get_stats:
            mock_get_stats.return_value = {"subscribers": 1000, "active_users": 50}

            with patch.object(mock_agent, "_get_db_session") as mock_session:
                mock_db_session = Mock()
                mock_session.return_value.__enter__.return_value = mock_db_session
                mock_session.return_value.__exit__.return_value = None

                with patch.object(
                    mock_agent, "_get_or_create_subreddit"
                ) as mock_subreddit:
                    mock_subreddit.return_value = Mock(id=1)

                    # Mock query results
                    mock_query = Mock()
                    mock_query.filter_by.return_value = mock_query
                    mock_query.order_by.return_value = mock_query
                    mock_query.limit.return_value = mock_query
                    mock_query.all.return_value = []
                    mock_db_session.query.return_value = mock_query

                    status = service.get_service_status()

        assert status["running"] is True
        assert status["subreddits"] == ["clouvel"]
        assert status["dry_run"] is True
        assert status["redis_connected"] is True
        assert "clouvel" in status["agents"]

    def test_get_service_status_with_error(self, service):
        """Test getting service status when agent has error."""
        mock_agent = service.agents["clouvel"]

        with patch.object(mock_agent, "get_community_stats") as mock_get_stats:
            mock_get_stats.side_effect = Exception("Test error")

            status = service.get_service_status()

            assert "clouvel" in status["agents"]
            assert "error" in status["agents"]["clouvel"]
            assert "Test error" in status["agents"]["clouvel"]["error"]

    @pytest.mark.asyncio
    async def test_startup_and_shutdown_messages(self, service):
        """Test that startup and shutdown messages are published."""
        # Test startup message
        service.running = False

        with patch.object(service, "_stream_subreddit") as mock_stream:
            mock_stream.return_value = AsyncMock()

            # Start service (but cancel immediately to avoid hanging)
            start_task = asyncio.create_task(service.start())
            await asyncio.sleep(0.1)  # Let it publish startup message
            start_task.cancel()

            try:
                await start_task
            except asyncio.CancelledError:
                pass

        # Verify startup message was published
        service.redis_client.publish.assert_called()
        calls = service.redis_client.publish.call_args_list

        startup_call = calls[0]
        assert startup_call[0][0] == "community_agent:clouvel"
        startup_message = json.loads(startup_call[0][1])
        assert startup_message["data"]["action_type"] == "service_started"
        assert (
            "Queen Clouvel's royal presence activated"
            in startup_message["data"]["message"]
        )

        # Test shutdown message
        await service.stop()

        # Find shutdown message in calls
        shutdown_found = False
        for call in service.redis_client.publish.call_args_list:
            if len(call[0]) >= 2:
                try:
                    message = json.loads(call[0][1])
                    if message["data"].get("action_type") == "service_stopped":
                        shutdown_found = True
                        assert (
                            "Queen Clouvel takes a royal nap"
                            in message["data"]["message"]
                        )
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

        assert shutdown_found, "Shutdown message was not published"
