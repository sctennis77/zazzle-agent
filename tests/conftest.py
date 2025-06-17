import os
import pytest
import shutil
from pathlib import Path

@pytest.fixture(scope="session", autouse=True)
def set_testing_environment():
    """Set the TESTING environment variable for all tests to use in-memory database."""
    os.environ['TESTING'] = 'true'
    yield
    # Clean up after all tests
    if 'TESTING' in os.environ:
        del os.environ['TESTING']

@pytest.fixture(scope="session")
def test_output_dir(tmp_path_factory):
    """Create a temporary directory for test outputs."""
    test_dir = tmp_path_factory.mktemp("test_outputs")
    yield test_dir
    # Cleanup after all tests are done
    shutil.rmtree(test_dir)

@pytest.fixture(autouse=True)
def set_test_output_dir(test_output_dir, monkeypatch):
    """Automatically set the test output directory for all tests."""
    # Override the default outputs directory for tests
    monkeypatch.setenv("OUTPUT_DIR", str(test_output_dir))
    # Create necessary subdirectories
    (test_output_dir / "screenshots").mkdir(exist_ok=True)
    (test_output_dir / "images").mkdir(exist_ok=True)
    return test_output_dir 