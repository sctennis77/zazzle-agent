import pytest
import logging
import io
import sys
import json
import time
import os
from app.utils.logging_config import (
    setup_logging, get_logger, StructuredLogFormatter, mask_sensitive, mask_env_dict, log_operation, log_timing, validate_environment_variables
)
from logging.handlers import RotatingFileHandler

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

def test_structured_log_formatter_basic():
    record = logging.LogRecord(
        name="test_structured",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Test structured log",
        args=(),
        exc_info=None
    )
    formatter = StructuredLogFormatter()
    output = formatter.format(record)
    data = json.loads(output)
    assert data["level"] == "INFO"
    assert data["message"] == "Test structured log"
    assert "timestamp" in data
    assert data["logger"] == "test_structured"

def test_structured_log_formatter_exception():
    try:
        raise ValueError("fail!")
    except Exception:
        record = logging.LogRecord(
            name="test_structured_exc",
            level=logging.ERROR,
            pathname=__file__,
            lineno=20,
            msg="Exception log",
            args=(),
            exc_info=sys.exc_info()
        )
        formatter = StructuredLogFormatter()
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "ERROR"
        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert "fail!" in data["exception"]["message"]

def test_structured_log_formatter_extra():
    record = logging.LogRecord(
        name="test_structured_extra",
        level=logging.INFO,
        pathname=__file__,
        lineno=30,
        msg="Extra log",
        args=(),
        exc_info=None
    )
    record.extra = {"foo": "bar", "baz": 123}
    formatter = StructuredLogFormatter()
    output = formatter.format(record)
    data = json.loads(output)
    assert data["foo"] == "bar"
    assert data["baz"] == 123

def test_mask_sensitive():
    assert mask_sensitive("API_KEY", "secret123") == "*********"
    assert mask_sensitive("password", "mypw") == "****"
    assert mask_sensitive("username", "user") == "user"

def test_mask_env_dict():
    env = {"API_KEY": "abc", "USER": "bob", "SECRET": "def"}
    masked = mask_env_dict(env)
    assert masked["API_KEY"] == "***"
    assert masked["SECRET"] == "***"
    assert masked["USER"] == "bob"

def test_log_operation_success_and_error(caplog):
    logger = get_logger("test_log_operation")
    with caplog.at_level(logging.INFO):
        log_operation(logger, "op1", "success", details={"foo": "bar"})
    found = False
    for rec in caplog.records:
        try:
            data = json.loads(rec.getMessage())
            if data.get("operation") == "op1" and data.get("status") == "success":
                found = True
        except Exception:
            continue
    assert found
    with caplog.at_level(logging.ERROR):
        log_operation(logger, "op2", "failure", details={"password": "1234"}, error=ValueError("fail"))
    found_fail = False
    found_mask = False
    for rec in caplog.records:
        try:
            data = json.loads(rec.getMessage())
            if data.get("operation") == "op2" and data.get("status") == "failure":
                found_fail = True
                if "****" in json.dumps(data):
                    found_mask = True
        except Exception:
            continue
    assert found_fail
    assert found_mask  # Masked password

def test_log_operation_non_serializable(caplog):
    logger = get_logger("test_log_operation_non_serializable")
    class Unserializable:
        pass
    with caplog.at_level(logging.INFO):
        log_operation(logger, "op3", "success", details={"obj": Unserializable()})
    assert "<non-serializable" in caplog.text

def test_log_timing_decorator(caplog):
    logger = get_logger("test_log_timing")
    @log_timing(logger, "timed_op")
    def slow_func():
        time.sleep(0.01)
        return 42
    with caplog.at_level(logging.INFO):
        result = slow_func()
    assert result == 42
    found = False
    found_duration = False
    for rec in caplog.records:
        try:
            data = json.loads(rec.getMessage())
            if data.get("operation") == "timed_op":
                found = True
                if "duration_seconds" in json.dumps(data):
                    found_duration = True
        except Exception:
            continue
    assert found
    assert found_duration

def test_validate_environment_variables(monkeypatch, caplog):
    """Test environment variable validation."""
    logger = logging.getLogger()  # Use root logger
    monkeypatch.setenv("FOO", "bar")
    monkeypatch.setenv("BAR", "baz")
    assert validate_environment_variables(["FOO", "BAR"], logger) is True
    
    # Remove one var
    monkeypatch.delenv("BAR")
    logger.setLevel(logging.ERROR)
    caplog.clear()
    
    with caplog.at_level(logging.ERROR):
        assert validate_environment_variables(["FOO", "BAR"], logger) is False
    
    found_missing = False
    for rec in caplog.records:
        if "Missing required environment variable: BAR" in rec.getMessage():
            found_missing = True
            break
    
    assert found_missing

def test_basic_logging_configuration():
    """Minimal test: configure logging, log a message, ensure file is created and contains the message."""
    log_dir = "logs"
    log_file = "test.log"
    log_path = os.path.join(log_dir, log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    setup_logging(log_file=log_path)
    logger = get_logger("zazzle_agent")
    test_message = "Test log message"
    logger.info(test_message)
    time.sleep(0.1)
    file_handler = next((h for h in logger.handlers if hasattr(h, 'baseFilename') and h.baseFilename.endswith(log_file)), None)
    if file_handler:
        file_handler.flush()
        file_handler.close()
        logger.removeHandler(file_handler)
    assert os.path.exists(log_path)
    with open(log_path, 'r') as f:
        assert test_message in f.read()
    if os.path.exists(log_path):
        os.remove(log_path)
    if os.path.exists(log_dir) and not os.listdir(log_dir):
        os.rmdir(log_dir)

def test_advanced_logging_configuration():
    """Minimal test: configure logging with DEBUG, log at all levels, ensure file contains all messages."""
    log_dir = "logs"
    log_file = "test_advanced.log"
    log_path = os.path.join(log_dir, log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    setup_logging(log_level="DEBUG", log_file=log_path, console_output=True)
    logger = get_logger("zazzle_agent")
    messages = [
        (logger.debug, "Debug message"),
        (logger.info, "Info message"),
        (logger.warning, "Warning message"),
        (logger.error, "Error message"),
    ]
    for log_func, msg in messages:
        log_func(msg)
    time.sleep(0.1)
    file_handler = next((h for h in logger.handlers if hasattr(h, 'baseFilename') and h.baseFilename.endswith(log_file)), None)
    if file_handler:
        file_handler.flush()
        file_handler.close()
        logger.removeHandler(file_handler)
    assert os.path.exists(log_path)
    with open(log_path, 'r') as f:
        log_content = f.read()
        for _, msg in messages:
            assert msg in log_content
    if os.path.exists(log_path):
        os.remove(log_path)
    if os.path.exists(log_dir) and not os.listdir(log_dir):
        os.rmdir(log_dir) 