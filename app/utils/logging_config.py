import os
import logging
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
import types

SENSITIVE_PATTERNS = ["KEY", "SECRET", "TOKEN", "PASSWORD"]

def mask_sensitive(key: str, value: str) -> str:
    """
    Mask sensitive values based on key patterns.
    """
    if any(pattern in key.upper() for pattern in SENSITIVE_PATTERNS):
        return "*" * len(str(value))
    return value

def mask_env_dict(env_dict: Dict[str, str]) -> Dict[str, str]:
    """
    Return a copy of the dict with sensitive values masked.
    """
    return {k: mask_sensitive(k, v) for k, v in env_dict.items()}

class StructuredLogFormatter(logging.Formatter):
    """Custom formatter that outputs logs in a structured JSON format."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if they exist
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
            
        # Add exception info if it exists
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
            
        return json.dumps(log_data)

def setup_logging(
    log_level: str = 'INFO',
    log_file: str = None,
    console_output: bool = True
) -> None:
    """
    Set up logging configuration for the application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to the log file (optional)
        console_output: Whether to output logs to console
    """
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file).parent
        log_path.mkdir(parents=True, exist_ok=True)
    
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    json_formatter = StructuredLogFormatter()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add file handler if log_file is specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)
    
    # Add console handler if console_output is True
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Set up specific loggers for different components
    component_loggers = {
        'app.agents': 'INFO',
        'app.clients': 'INFO',
        'app.distribution': 'INFO',
        'app.utils': 'INFO',
        # Reduce noise from third-party libraries
        'httpx': 'WARNING',
        'praw': 'WARNING',
        'openai': 'WARNING',
    }
    
    for logger_name, level in component_loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level))

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: The name of the logger
        
    Returns:
        logging.Logger: A configured logger instance
    """
    return logging.getLogger(name)

def safe_serialize(obj):
    try:
        json.dumps(obj)
        return obj
    except (TypeError, OverflowError):
        return f"<non-serializable: {type(obj).__name__}>"

def log_operation(
    logger: logging.Logger,
    operation: str,
    status: str,
    details: Dict[str, Any] = None,
    error: Exception = None,
    duration: Optional[float] = None
) -> None:
    """
    Log an operation with structured details.
    
    Args:
        logger: The logger instance to use
        operation: The name of the operation
        status: The status of the operation (success, failure, etc.)
        details: Additional details about the operation
        error: Exception object if the operation failed
        duration: Duration of the operation in seconds
    """
    # Mask sensitive values in details if present
    if details:
        details = {
            k: mask_sensitive(k, v) if isinstance(v, str) else safe_serialize(v)
            for k, v in details.items()
        }
    log_data = {
        'operation': operation,
        'status': status,
        'timestamp': datetime.now().isoformat()
    }
    
    if details:
        log_data['details'] = details
        
    if duration is not None:
        log_data['duration_seconds'] = duration
        
    if error:
        log_data['error'] = {
            'type': error.__class__.__name__,
            'message': str(error)
        }
        logger.error(json.dumps(log_data))
    else:
        logger.info(json.dumps(log_data))

def log_timing(logger: logging.Logger, operation: str):
    """
    Decorator to log the timing of an operation.
    
    Args:
        logger: The logger instance to use
        operation: The name of the operation
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                log_operation(
                    logger,
                    operation,
                    'success',
                    {'duration_seconds': duration}
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_operation(
                    logger,
                    operation,
                    'failure',
                    {'duration_seconds': duration},
                    error=e
                )
                raise
        return wrapper
    return decorator

def validate_environment_variables(required_vars: List[str], logger: logging.Logger) -> bool:
    """
    Validate that required environment variables are set.
    
    Args:
        required_vars: List of required environment variable names
        logger: Logger instance to use
        
    Returns:
        bool: True if all variables are set, False otherwise
    """
    env_dict = {var: os.getenv(var, "") for var in required_vars}
    masked_env = mask_env_dict(env_dict)
    missing_vars = [var for var, v in env_dict.items() if not v]
    
    if missing_vars:
        log_operation(
            logger,
            'environment_validation',
            'failure',
            {'missing_variables': missing_vars, 'env': masked_env}
        )
        return False
    
    log_operation(
        logger,
        'environment_validation',
        'success',
        {'validated_variables': list(masked_env.keys()), 'env': masked_env}
    )
    return True 