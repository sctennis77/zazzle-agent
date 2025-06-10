import pytest
import logging
from app.utils.logging_config import setup_logging, get_logger

def test_setup_logging():
    """Test that setup_logging runs without error."""
    setup_logging()

def test_get_logger():
    """Test getting a logger instance."""
    setup_logging()
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
    # Logging should not raise
    logger.info("Test log handler creation")

def test_logger_levels():
    """Test logging at different levels does not raise."""
    setup_logging()
    logger = get_logger("test_levels")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

def test_logger_formatting():
    """Test log message formatting does not raise."""
    setup_logging()
    logger = get_logger("test_formatting")
    logger.info("Test message")

def test_multiple_loggers():
    """Test creating multiple logger instances."""
    setup_logging()
    logger1 = get_logger("logger1")
    logger2 = get_logger("logger2")
    assert logger1 is not logger2
    assert logger1.name == "logger1"
    assert logger2.name == "logger2"
    logger1.info("Logger1 message")
    logger2.info("Logger2 message")

def test_logger_cleanup():
    """Test logger cleanup and recreation does not raise."""
    setup_logging()
    logger1 = get_logger("test_cleanup")
    logger1.info("First message")
    logger2 = get_logger("test_cleanup")
    logger2.info("Second message")
    assert logger1 is logger2 