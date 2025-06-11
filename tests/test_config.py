"""
Test configuration and settings.

This module contains configuration settings and fixtures for the test suite.
"""

import os
import pytest
import json
from pathlib import Path
from typing import Dict, Any

# Test configuration
TEST_CONFIG = {
    "api_retry_attempts": 3,
    "api_retry_delay": 1,
    "concurrent_operations": 3,
    "test_data_dir": "tests/test_data",
    "mock_responses_dir": "tests/mock_responses"
}

# Create test directories
def setup_test_directories():
    """Create necessary test directories."""
    for directory in [TEST_CONFIG["test_data_dir"], TEST_CONFIG["mock_responses_dir"]]:
        Path(directory).mkdir(parents=True, exist_ok=True)

@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration to tests."""
    setup_test_directories()
    return TEST_CONFIG

@pytest.fixture(scope="session")
def mock_api_responses():
    """Load mock API responses for testing."""
    responses = {}
    mock_dir = Path(TEST_CONFIG["mock_responses_dir"])
    
    for file in mock_dir.glob("*.json"):
        with open(file) as f:
            responses[file.stem] = json.load(f)
    
    return responses

@pytest.fixture(scope="session")
def test_data():
    """Load test data for testing."""
    data = {}
    data_dir = Path(TEST_CONFIG["test_data_dir"])
    
    for file in data_dir.glob("*.json"):
        with open(file) as f:
            data[file.stem] = json.load(f)
    
    return data

@pytest.fixture(autouse=True)
def setup_test_environment(test_config):
    """Set up test environment variables."""
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["API_RETRY_ATTEMPTS"] = str(test_config["api_retry_attempts"])
    os.environ["API_RETRY_DELAY"] = str(test_config["api_retry_delay"])
    os.environ["CONCURRENT_OPERATIONS"] = str(test_config["concurrent_operations"])
    
    yield
    
    # Clean up environment variables
    for key in ["TESTING", "API_RETRY_ATTEMPTS", "API_RETRY_DELAY", "CONCURRENT_OPERATIONS"]:
        os.environ.pop(key, None)

def create_mock_response(name: str, data: Dict[str, Any]):
    """Create a mock API response file."""
    file_path = Path(TEST_CONFIG["mock_responses_dir"]) / f"{name}.json"
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

def create_test_data(name: str, data: Dict[str, Any]):
    """Create a test data file."""
    file_path = Path(TEST_CONFIG["test_data_dir"]) / f"{name}.json"
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2) 