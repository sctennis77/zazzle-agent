import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
from pathlib import Path
from app.clients.imgur_client import ImgurClient

class TestImgurClient(unittest.TestCase):
    """Test cases for the ImgurClient class."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_client_id = "test_client_id"
        self.mock_client_secret = "test_client_secret"
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'IMGUR_CLIENT_ID': self.mock_client_id,
            'IMGUR_CLIENT_SECRET': self.mock_client_secret
        })
        self.env_patcher.start()
        
        self.imgur_client = ImgurClient()
        
    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
        
    def test_init_with_credentials(self):
        """Test initialization with valid credentials."""
        self.assertEqual(self.imgur_client.client_id, self.mock_client_id)
        self.assertEqual(self.imgur_client.client_secret, self.mock_client_secret)
        self.assertEqual(
            self.imgur_client.headers['Authorization'],
            f'Client-ID {self.mock_client_id}'
        )
        
    def test_init_without_credentials(self):
        """Test initialization without credentials."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                ImgurClient()
                
    @patch('requests.post')
    def test_upload_image_success(self, mock_post):
        """Test successful image upload."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'data': {'link': 'https://imgur.com/test_image.jpg'}
        }
        mock_post.return_value = mock_response
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=b'test_image_data')):
                imgur_url, local_path = self.imgur_client.upload_image('test_image.png')
                
                self.assertEqual(imgur_url, 'https://imgur.com/test_image.jpg')
                self.assertEqual(local_path, 'test_image.png')
                mock_post.assert_called_once()
                
    @patch('requests.post')
    def test_upload_image_failure(self, mock_post):
        """Test image upload failure."""
        # Mock response with error
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'success': False,
            'data': {'error': 'Upload failed'}
        }
        mock_post.return_value = mock_response
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=b'test_image_data')):
                with self.assertRaises(Exception):
                    self.imgur_client.upload_image('test_image.png')
                    
    def test_upload_nonexistent_image(self):
        """Test uploading a non-existent image."""
        with patch('os.path.exists', return_value=False):
            with self.assertRaises(ValueError):
                self.imgur_client.upload_image('nonexistent.png')
                
    def test_save_image_locally(self):
        """Test saving image locally."""
        test_data = b'test_image_data'
        test_filename = 'test_image.png'
        
        # Mock Path and file operations
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            with patch('builtins.open', mock_open()) as mock_file:
                local_path = self.imgur_client.save_image_locally(test_data, test_filename)
                
                # Verify directory creation
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
                
                # Verify file writing
                mock_file.assert_called_once()
                mock_file().write.assert_called_once_with(test_data)
                
                # Verify path
                self.assertEqual(local_path, str(Path('outputs') / test_filename)) 