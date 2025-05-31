"""
Logging configuration and utilities
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import settings


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging():
    """Setup logging configuration for the application"""
    
    # Create logs directory
    logs_dir = Path(settings.logs_directory)
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / 'pipeline_system.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt=settings.log_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Error handler for error logs only
    error_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / 'errors.log',
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Execution logs handler
    execution_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / 'executions.log',
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=10,
        encoding='utf-8'
    )
    execution_handler.setLevel(logging.INFO)
    execution_handler.setFormatter(file_formatter)
    
    # Add execution handler to specific loggers
    execution_logger = logging.getLogger('app.pipeline_engine')
    execution_logger.addHandler(execution_handler)
    
    # Reduce verbosity of external libraries
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)


class ExecutionLogger:
    """Special logger for pipeline executions"""
    
    def __init__(self, execution_id: str, pipeline_name: str):
        self.execution_id = execution_id
        self.pipeline_name = pipeline_name
        self.logger = get_logger(f'execution.{execution_id}')
        self.logs = []
    
    def info(self, message: str):
        """Log info message"""
        log_entry = f"[{datetime.utcnow().isoformat()}] INFO: {message}"
        self.logs.append(log_entry)
        self.logger.info(f"[{self.pipeline_name}] {message}")
    
    def warning(self, message: str):
        """Log warning message"""
        log_entry = f"[{datetime.utcnow().isoformat()}] WARNING: {message}"
        self.logs.append(log_entry)
        self.logger.warning(f"[{self.pipeline_name}] {message}")
    
    def error(self, message: str):
        """Log error message"""
        log_entry = f"[{datetime.utcnow().isoformat()}] ERROR: {message}"
        self.logs.append(log_entry)
        self.logger.error(f"[{self.pipeline_name}] {message}")
    
    def debug(self, message: str):
        """Log debug message"""
        log_entry = f"[{datetime.utcnow().isoformat()}] DEBUG: {message}"
        self.logs.append(log_entry)
        self.logger.debug(f"[{self.pipeline_name}] {message}")
    
    def get_logs(self) -> list:
        """Get all logged messages for this execution"""
        return self.logs.copy()


def create_execution_logger(execution_id: str, pipeline_name: str) -> ExecutionLogger:
    """Create a new execution logger"""
    return ExecutionLogger(execution_id, pipeline_name)


class AuditLogger:
    """Logger for audit events"""
    
    def __init__(self):
        self.logger = get_logger('audit')
        
        # Setup audit file handler if not already configured
        if not any(isinstance(h, logging.FileHandler) and 'audit' in h.baseFilename 
                  for h in self.logger.handlers):
            
            logs_dir = Path(settings.logs_directory)
            logs_dir.mkdir(exist_ok=True)
            
            audit_handler = logging.handlers.RotatingFileHandler(
                filename=logs_dir / 'audit.log',
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=10,
                encoding='utf-8'
            )
            audit_handler.setLevel(logging.INFO)
            
            audit_formatter = logging.Formatter(
                fmt='%(asctime)s - AUDIT - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            audit_handler.setFormatter(audit_formatter)
            self.logger.addHandler(audit_handler)
    
    def log_event(self, event_type: str, details: dict, user_id: str = None):
        """Log an audit event"""
        audit_data = {
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'details': details
        }
        
        message = f"{event_type} - User: {user_id or 'system'} - Details: {details}"
        self.logger.info(message)


# Global audit logger instance
audit_logger = AuditLogger()
