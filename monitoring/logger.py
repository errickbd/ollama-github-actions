#!/usr/bin/env python3
"""
Advanced logging module for enterprise workflow monitoring.
Provides structured logging with multiple output formats and levels.
"""

import logging
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from monitoring.correlation import get_correlation_id


class JsonFormatter(logging.Formatter):
    """Custom formatter for JSON log output."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        return json.dumps(log_entry)


class WorkflowLogger:
    """Enterprise-grade logger for workflow automation."""
    
    def __init__(self, name="workflow", log_dir="logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        
        self._setup_console_handler()
        self._setup_file_handler()
        self._setup_json_handler()

    def _setup_console_handler(self):
        """Setup console output with formatted messages."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self):
        """Setup file output for persistent logging."""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"{self.name}-{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def _setup_json_handler(self):
        """Setup JSON output for structured logging."""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        json_file = self.log_dir / f"{self.name}-{timestamp}.json"
        
        json_handler = logging.FileHandler(json_file)
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(JsonFormatter())
        self.logger.addHandler(json_handler)

    def info(self, message, **kwargs):
        """Log info level message with correlation ID."""
        corr_id = get_correlation_id()
        full_message = f"[{corr_id}] {message}"
        if kwargs:
            full_message = f"{full_message} | Context: {json.dumps(kwargs)}"
        self.logger.info(full_message)
    
    def error(self, message, **kwargs):
        """Log error level message with correlation ID."""
        corr_id = get_correlation_id()
        full_message = f"[{corr_id}] {message}"
        if kwargs:
            full_message = f"{full_message} | Context: {json.dumps(kwargs)}"
        self.logger.error(full_message)
    
    def warning(self, message, **kwargs):
        """Log warning level message with correlation ID."""
        corr_id = get_correlation_id()
        full_message = f"[{corr_id}] {message}"
        if kwargs:
            full_message = f"{full_message} | Context: {json.dumps(kwargs)}"
        self.logger.warning(full_message)
    
    def debug(self, message, **kwargs):
        """Log debug level message with correlation ID."""
        corr_id = get_correlation_id()
        full_message = f"[{corr_id}] {message}"
        if kwargs:
            full_message = f"{full_message} | Context: {json.dumps(kwargs)}"
        self.logger.debug(full_message)

    @contextmanager
    def timer(self, operation_name):
        """Context manager for timing operations."""
        start_time = time.time()
        self.info(f"Starting: {operation_name}")
        
        try:
            yield
            duration = time.time() - start_time
            self.info(f"Completed: {operation_name} ({duration:.2f}s)")
        except Exception as e:
            duration = time.time() - start_time
            self.error(f"Failed: {operation_name} ({duration:.2f}s) - {str(e)}")
            raise

    def metric(self, metric_name, value, unit="", **tags):
        """Log a metric value with optional tags."""
        metric_data = {
            'metric_name': metric_name,
            'value': value,
            'unit': unit,
            'tags': tags
        }
        self.info(f"METRIC: {metric_name}={value}{unit}", **metric_data)


if __name__ == "__main__":
    from monitoring.correlation import generate_correlation_id
    generate_correlation_id()
    
    logger = WorkflowLogger("test")
    
    logger.info("Starting test workflow")
    
    with logger.timer("test_operation"):
        time.sleep(1)
    
    logger.metric("test_count", 42, unit=" items")
    logger.info("Test completed successfully")
