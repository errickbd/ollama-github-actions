#!/usr/bin/env python3
"""
Monitoring dashboard for workflow observability.
Integrates logging, metrics, and health checks.
"""

import json
import sys
import shutil
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from monitoring.logger import WorkflowLogger
from cloud.s3_manager import S3Manager

class WorkflowMonitor:
    """Comprehensive monitoring for workflow automation."""
    
    def __init__(self, workflow_name="ollama-workflow"):
        self.workflow_name = workflow_name
        self.logger = WorkflowLogger(workflow_name)
        self.s3_manager = S3Manager()
        self.start_time = datetime.now()
        self.workflow_run = None
        self.commit_sha = None
    
    def start_monitoring(self, workflow_run, commit_sha):
        """Initialize monitoring for a workflow run."""
        self.workflow_run = workflow_run
        self.commit_sha = commit_sha
        
        self.logger.info("Starting workflow monitoring",
                        workflow_run=workflow_run,
                        commit_sha=commit_sha)
        
    def monitor_operation(self, operation_name, duration, success=True):
        """Record performance metrics for operations."""
        status = "success" if success else "failure"
        self.logger.metric(f"{operation_name}_duration", round(duration, 2), unit="s")
        self.logger.metric(f"{operation_name}_status", 1 if success else 0)
        
        thresholds = {
            'ollama_query': 60,
            'model_download': 300,
            'test_execution': 30,
            's3_upload': 60
        }
        
        threshold = thresholds.get(operation_name, 120)
        if duration > threshold:
            self.logger.warning(f"Performance threshold exceeded: {operation_name}",
                              duration=duration, threshold=threshold)
            
    def health_check(self):
        """Perform comprehensive health check."""
        health = {
            'timestamp': datetime.now().isoformat(),
            'workflow_run': self.workflow_run,
            'checks': {}
        }
        
        # Check disk space
        total, used, free = shutil.disk_usage('/')
        free_percent = (free / total) * 100
        health['checks']['disk_space'] = {
            'status': 'healthy' if free_percent > 10 else 'warning',
            'free_percent': round(free_percent, 1)
        }
        
        # Check logs directory
        logs_dir = Path('logs')
        health['checks']['logs_directory'] = {
            'status': 'healthy' if logs_dir.exists() else 'warning',
            'exists': logs_dir.exists()
        }
        
        # Check S3 connectivity
        s3_ok = self.s3_manager.check_aws_configured()
        health['checks']['aws_configured'] = {
            'status': 'healthy' if s3_ok else 'degraded',
            'configured': s3_ok
        }
        
        self.logger.info("Health check completed", **health)
        return health
    
    def track_error(self, error_type, error_message, context=None):
        """Track and categorize errors."""
        error_data = {
            'error_type': error_type,
            'error_message': str(error_message),
            'workflow_run': self.workflow_run,
            'context': context or {}
        }
        
        self.logger.error(f"Error: {error_type}", **error_data)
        
        critical_errors = ['ollama_service_down', 'model_download_failed']
        if error_type in critical_errors:
            self.logger.error(f"CRITICAL: {error_type} - {error_message}")

    def generate_summary(self, result_dir):
        """Generate workflow summary report."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        summary = {
            'workflow_name': self.workflow_name,
            'workflow_run': self.workflow_run,
            'commit_sha': self.commit_sha,
            'start_time': self.start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': round(duration, 2),
            'health': self.health_check()
        }
        
        result_dir = Path(result_dir)
        result_dir.mkdir(parents=True, exist_ok=True)
        
        summary_file = result_dir / 'monitoring_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info("Summary generated", file=str(summary_file))
        return summary
    
if __name__ == "__main__":
    monitor = WorkflowMonitor("test-workflow")
    monitor.start_monitoring("999", "abc123")
    
    import time
    with monitor.logger.timer("test_operation"):
        time.sleep(1)
    
    monitor.monitor_operation("test_operation", 1.0, success=True)
    
    health = monitor.health_check()
    print(f"\nHealth status: {json.dumps(health['checks'], indent=2)}")
    
    summary = monitor.generate_summary("test-results")
    print(f"\nSummary saved to: test-results/monitoring_summary.json")