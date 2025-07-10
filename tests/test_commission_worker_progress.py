import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock
from app.commission_worker import CommissionWorker

class TestCommissionWorkerProgress(unittest.TestCase):
    @patch('app.commission_worker.time.sleep', return_value=None)
    @patch('app.commission_worker.random.uniform', return_value=1.5)
    def test_incremental_progress_updates(self, mock_random, mock_sleep):
        # Arrange
        worker = CommissionWorker(donation_id=1, task_data={})
        worker._update_task_status = MagicMock()
        donation = MagicMock()
        
        # Act
        worker._send_incremental_progress_updates(donation)
        
        # Assert
        calls = worker._update_task_status.call_args_list
        progresses = [call.kwargs['progress'] for call in calls]
        stages = [call.kwargs['stage'] for call in calls]
        messages = [call.kwargs['message'] for call in calls]
        
        # Should start at 40 and end at 89
        self.assertEqual(progresses[0], 40)
        self.assertEqual(progresses[-1], 89)
        self.assertTrue(all(40 <= p <= 89 for p in progresses))
        self.assertTrue(all(s == 'image_generation_in_progress' for s in stages))
        self.assertTrue(all('Image generation in progress' in m for m in messages))
        self.assertGreater(len(progresses), 5)  # Should be multiple updates
        
        # Verify random.uniform was called for each sleep interval
        self.assertEqual(mock_random.call_count, len(progresses) - 1)  # One less than updates
        # Verify each call was with the correct range
        for call in mock_random.call_args_list:
            self.assertEqual(call[0], (1.0, 2.5))

    @patch('app.commission_worker.time.sleep', return_value=None)
    @patch('app.commission_worker.random.uniform', return_value=1.5)
    def test_incremental_progress_updates_stop_flag(self, mock_random, mock_sleep):
        """Test that the progress thread stops when the stop flag is set."""
        # Arrange
        worker = CommissionWorker(donation_id=1, task_data={})
        worker._update_task_status = MagicMock()
        donation = MagicMock()
        
        # Set the stop flag after a few iterations
        original_sleep = worker._send_incremental_progress_updates.__globals__['time'].sleep
        call_count = 0
        
        def mock_sleep_with_stop(duration):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:  # Stop after 3 sleep calls
                worker._stop_progress_thread = True
            original_sleep(duration)
        
        with patch('app.commission_worker.time.sleep', side_effect=mock_sleep_with_stop):
            # Act
            worker._send_incremental_progress_updates(donation)
            
            # Assert
            calls = worker._update_task_status.call_args_list
            # Should have fewer calls than normal due to early stop
            self.assertLess(len(calls), 30)
            self.assertGreater(len(calls), 0)  # Should have at least some calls

    async def test_broadcast_image_generation_started(self):
        """Test that the image generation started broadcast uses the correct message format."""
        # Arrange
        worker = CommissionWorker(donation_id=1, task_data={})
        worker._update_task_status = MagicMock()
        
        # Mock donation with subreddit and post_id
        donation = MagicMock()
        donation.post_id = "abc123"
        donation.subreddit = MagicMock()
        donation.subreddit.subreddit_name = "golf"
        
        # Act
        await worker._broadcast_image_generation_started({"post_id": "abc123"}, donation)
        
        # Assert
        worker._update_task_status.assert_called_once()
        call_args = worker._update_task_status.call_args
        self.assertEqual(call_args[1]['progress'], 40)
        self.assertEqual(call_args[1]['stage'], 'image_generation_started')
        self.assertEqual(call_args[1]['message'], 'Clouvel illustrating abc123 from r/golf')

    async def test_broadcast_image_generation_started_no_subreddit(self):
        """Test that the image generation started broadcast handles missing subreddit gracefully."""
        # Arrange
        worker = CommissionWorker(donation_id=1, task_data={})
        worker._update_task_status = MagicMock()
        
        # Mock donation without subreddit
        donation = MagicMock()
        donation.post_id = "abc123"
        donation.subreddit = None
        
        # Act
        await worker._broadcast_image_generation_started({"post_id": "abc123"}, donation)
        
        # Assert
        worker._update_task_status.assert_called_once()
        call_args = worker._update_task_status.call_args
        self.assertEqual(call_args[1]['progress'], 40)
        self.assertEqual(call_args[1]['stage'], 'image_generation_started')
        self.assertEqual(call_args[1]['message'], 'Clouvel illustrating abc123 from r/unknown')

if __name__ == '__main__':
    unittest.main() 