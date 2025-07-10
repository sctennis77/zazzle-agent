import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from unittest.mock import patch, MagicMock
from app.commission_worker import CommissionWorker

class TestCommissionWorkerProgress(unittest.TestCase):
    @patch('app.commission_worker.time.sleep', return_value=None)
    def test_incremental_progress_updates(self, mock_sleep):
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
        
        # Should start at 40 and end at 70
        self.assertEqual(progresses[0], 40)
        self.assertEqual(progresses[-1], 70)
        self.assertTrue(all(40 <= p <= 70 for p in progresses))
        self.assertTrue(all(s == 'image_generation_in_progress' for s in stages))
        self.assertTrue(all('Image generation in progress' in m for m in messages))
        self.assertGreater(len(progresses), 5)  # Should be multiple updates

if __name__ == '__main__':
    unittest.main() 