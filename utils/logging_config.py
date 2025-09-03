"""
Structured Logging Configuration for DBI Operations Hub
Provides centralized logging setup with proper formatting and handlers.
"""
import os
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record):
        # Add structured fields
        if not hasattr(record, 'module'):
            record.module = record.name
        if not hasattr(record, 'operation'):
            record.operation = getattr(record, 'funcName', 'unknown')
        if not hasattr(record, 'user_id'):
            record.user_id = getattr(record, 'user_id', 'system')
        
        return super().format(record)


def setup_logging(app_name: str = "dbi_operations_hub", log_level: str = None) -> logging.Logger:
    """
    Setup structured logging for the application
    
    Args:
        app_name: Name of the application
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    # Determine log level
    if log_level is None:
        log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, log_level))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = StructuredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(module)s.%(operation)s | %(user_id)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = StructuredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / f'{app_name}.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / f'{app_name}_errors.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(f"dbi_operations_hub.{name}")


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for the class"""
        class_name = self.__class__.__name__
        module_name = self.__class__.__module__.split('.')[-1]
        return get_logger(f"{module_name}.{class_name}")
    
    def log_operation(self, message: str, level: int = logging.INFO, 
                     operation: str = None, user_id: str = None, **kwargs):
        """Log an operation with structured data"""
        extra = {
            'operation': operation or 'unknown',
            'user_id': user_id or 'system'
        }
        extra.update(kwargs)
        
        self.logger.log(level, message, extra=extra)
    
    def log_error(self, message: str, exc_info=True, operation: str = None, 
                  user_id: str = None, **kwargs):
        """Log an error with full context"""
        extra = {
            'operation': operation or 'unknown', 
            'user_id': user_id or 'system'
        }
        extra.update(kwargs)
        
        self.logger.error(message, exc_info=exc_info, extra=extra)
