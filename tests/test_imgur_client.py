import importlib
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests


class TestImgurClient:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        os.environ["OUTPUT_DIR"] = self.temp_dir
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        import app.clients.imgur_client

        importlib.reload(app.clients.imgur_client)
        from app.clients.imgur_client import ImgurClient

        self.ImgurClient = ImgurClient
        self.imgur_client = self.ImgurClient()

    def teardown_method(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)

    def test_save_image_locally(self):
        test_data = b"test_image_data"
        test_filename = "test_image.png"
        subdirectory = "generated_products"
        print(f"DEBUG: OUTPUT_DIR={os.getenv('OUTPUT_DIR')}")
        local_path = self.imgur_client.save_image_locally(
            test_data, test_filename, subdirectory=subdirectory
        )
        print(f"DEBUG: save_image_locally returned: {local_path}")
        print(f"DEBUG: os.path.exists(local_path): {os.path.exists(local_path)}")
        assert os.path.exists(local_path)
        with open(local_path, "rb") as f:
            assert f.read() == test_data
        expected_path = local_path
        print(f"DEBUG: expected_path: {expected_path}")
        assert os.path.abspath(local_path) == os.path.abspath(expected_path)

    @patch("requests.post")
    def test_upload_image_success(self, mock_post):
        # Create a real file to upload
        file_path = os.path.join(self.temp_dir, "test.png")
        with open(file_path, "wb") as f:
            f.write(b"test_image_data")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"link": "https://i.imgur.com/test.png"},
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        imgur_url, local_path = self.imgur_client.upload_image(file_path)
        print(f"DEBUG: upload_image returned local_path: {local_path}")
        print(f"DEBUG: file_path: {file_path}")
        assert imgur_url == "https://i.imgur.com/test.png"
        assert os.path.samefile(local_path, file_path)

    @patch("requests.post")
    def test_upload_image_failure(self, mock_post):
        # Create a real file to upload
        file_path = os.path.join(self.temp_dir, "test.png")
        with open(file_path, "wb") as f:
            f.write(b"test_image_data")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "data": {"error": "Upload failed"},
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        with pytest.raises(requests.exceptions.RequestException):
            self.imgur_client.upload_image(file_path)

    def test_upload_nonexistent_image(self):
        file_path = os.path.join(self.temp_dir, "does_not_exist.png")
        print(f"DEBUG: test_upload_nonexistent_image file_path: {file_path}")
        assert not os.path.exists(file_path)
        with pytest.raises(ValueError, match="Image file not found"):
            self.imgur_client.upload_image(file_path)
