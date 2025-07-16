import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import MagicMock, patch

import pytest

from app.commission_worker import CommissionWorker


class TestCommissionWorkerProgress(unittest.TestCase):
    def test_incremental_progress_updates(self):
        # This test is no longer relevant since progress updates are now handled by RedditAgent
        # The CommissionWorker no longer has _send_incremental_progress_updates method
        pass

    def test_incremental_progress_updates_stop_flag(self):
        # This test is no longer relevant since progress updates are now handled by RedditAgent
        # The CommissionWorker no longer has _send_incremental_progress_updates method or _stop_progress_thread flag
        pass

    @pytest.mark.asyncio
    async def test_progress_callback_image_generation_started(self):
        """Test that the progress callback handles image_generation_started stage correctly."""
        # Arrange
        worker = CommissionWorker(donation_id=1, task_data={})
        worker._update_task_status = MagicMock()

        # Act
        await worker._progress_callback(
            "image_generation_started", {"post_id": "abc123", "subreddit_name": "golf"}
        )

        # Assert
        worker._update_task_status.assert_called_once()
        call_args = worker._update_task_status.call_args
        self.assertEqual(call_args[1]["progress"], 40)
        self.assertEqual(call_args[1]["stage"], "image_generation_started")
        self.assertEqual(
            call_args[1]["message"], "Clouvel started working on abc123 from r/golf"
        )

    @pytest.mark.asyncio
    async def test_progress_callback_image_generation_started_no_subreddit(self):
        """Test that the progress callback handles missing subreddit gracefully."""
        # Arrange
        worker = CommissionWorker(donation_id=1, task_data={})
        worker._update_task_status = MagicMock()

        # Act
        await worker._progress_callback(
            "image_generation_started", {"post_id": "abc123", "subreddit_name": None}
        )

        # Assert
        worker._update_task_status.assert_called_once()
        call_args = worker._update_task_status.call_args
        self.assertEqual(call_args[1]["progress"], 40)
        self.assertEqual(call_args[1]["stage"], "image_generation_started")
        self.assertEqual(
            call_args[1]["message"], "Clouvel started working on abc123 from r/unknown"
        )

    @pytest.mark.asyncio
    async def test_progress_callback_image_generation_progress(self):
        """Test that the progress callback handles image_generation_progress stage correctly."""
        # Arrange
        worker = CommissionWorker(donation_id=1, task_data={})
        worker._update_task_status = MagicMock()

        # Act
        await worker._progress_callback("image_generation_progress", {"progress": 65})

        # Assert
        worker._update_task_status.assert_called_once()
        call_args = worker._update_task_status.call_args
        self.assertEqual(call_args[1]["progress"], 65)
        self.assertEqual(call_args[1]["stage"], "image_generation_in_progress")
        self.assertEqual(
            call_args[1]["message"], "Clouvel illustrating ...  (65%)"
        )

    @pytest.mark.asyncio
    async def test_progress_callback_image_generation_complete(self):
        """Test that the progress callback handles image_generation_complete stage correctly."""
        # Arrange
        worker = CommissionWorker(donation_id=1, task_data={})
        worker._update_task_status = MagicMock()

        # Act
        await worker._progress_callback("image_generation_complete", {})

        # Assert
        worker._update_task_status.assert_called_once()
        call_args = worker._update_task_status.call_args
        self.assertEqual(call_args[1]["progress"], 90)
        self.assertEqual(call_args[1]["stage"], "image_generated")
        self.assertEqual(call_args[1]["message"], "Image generated successfully")


if __name__ == "__main__":
    unittest.main()
