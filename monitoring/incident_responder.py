#!/usr/bin/env python3
"""
Incident response module for automated recovery.
Attempts to fix problems before alerting humans.
"""

import subprocess
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitoring.correlation import get_correlation_id


class IncidentResponder:
    """Automated incident response with recovery logic."""
    
    def __init__(self, logger=None, notifier=None, max_attempts=3):
        self.logger = logger
        self.notifier = notifier
        self.max_attempts = max_attempts
        self.attempts = {}
        
        self._log("IncidentResponder initialized")
    
    def _log(self, message):
        """Log via logger or print with correlation ID."""
        if self.logger:
            self.logger.info(message)
        else:
            corr_id = get_correlation_id()
            print(f"[{corr_id}] {message}")
    
    def _escalate(self, incident_type, error, attempts):
        """Escalate to human via notification."""
        self._log(f"ESCALATING: {incident_type} after {attempts} failed attempts")
        
        if self.notifier:
            self.notifier.send_alert(
                f"Incident: {incident_type}",
                f"Error: {error}\nRecovery attempts: {attempts}\nManual intervention required.",
                "CRITICAL"
            )
        else:
            self._log("No notifier configured - escalation logged only")
    
    def handle_model_failure(self, model_name, error):
        """
        Try to recover from model download failure.
        
        Args:
            model_name: Name of the model that failed
            error: Error message from the failure
        
        Returns:
            True if recovery successful, False if escalated
        """
        key = f"model_{model_name}"
        attempt = self.attempts.get(key, 0) + 1
        self.attempts[key] = attempt
        
        self._log(f"Recovery attempt {attempt}/{self.max_attempts} for model: {model_name}")
        self._log(f"Original error: {error}")
        
        # Check if we've exceeded max attempts
        if attempt > self.max_attempts:
            self._escalate("model_download_failed", error, attempt - 1)
            return False
        
        # Wait with exponential backoff
        delay = 2 ** (attempt - 1)  # 1s, 2s, 4s
        self._log(f"Waiting {delay}s before retry...")
        time.sleep(delay)
        
        # Try to download the model again
        try:
            self._log(f"Retrying download of {model_name}...")
            result = subprocess.run(
                ['ollama', 'pull', model_name],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                self._log(f"Recovery successful! Model {model_name} downloaded.")
                self.attempts[key] = 0  # Reset attempt counter
                return True
            else:
                self._log(f"Download failed: {result.stderr}")
                return self.handle_model_failure(model_name, result.stderr)
                
        except subprocess.TimeoutExpired:
            self._log("Download timed out")
            return self.handle_model_failure(model_name, "Timeout after 300s")
        except FileNotFoundError:
            self._log("Ollama not installed")
            self._escalate("ollama_not_installed", "Ollama CLI not found", attempt)
            return False
        except Exception as e:
            self._log(f"Unexpected error: {e}")
            return self.handle_model_failure(model_name, str(e))
    
    def handle_s3_failure(self, operation, error):
        """
        Try to recover from S3 failure.
        
        Args:
            operation: Description of the failed operation
            error: Error message from the failure
        
        Returns:
            True if recovery successful, False if escalated
        """
        key = f"s3_{operation}"
        attempt = self.attempts.get(key, 0) + 1
        self.attempts[key] = attempt
        
        self._log(f"S3 recovery attempt {attempt}/{self.max_attempts}: {operation}")
        
        if attempt > self.max_attempts:
            self._escalate("s3_operation_failed", f"{operation}: {error}", attempt - 1)
            return False
        
        # Wait with backoff
        delay = 2 ** (attempt - 1)
        self._log(f"Waiting {delay}s before retry...")
        time.sleep(delay)
        
        # For S3, we just signal to retry - actual retry happens in caller
        self._log("Ready to retry S3 operation")
        return True
    
    def get_incident_summary(self):
        """Get summary of all incidents handled."""
        return {
            'total_incidents': len(self.attempts),
            'incidents': dict(self.attempts)
        }


if __name__ == "__main__":
    from monitoring.correlation import generate_correlation_id
    generate_correlation_id()
    
    print("=" * 50)
    print("Testing Incident Responder")
    print("=" * 50)
    
    responder = IncidentResponder(max_attempts=2)
    
    # Test with a fake model (will fail and escalate)
    print("\nTesting recovery with fake model (will fail):")
    print("-" * 50)
    result = responder.handle_model_failure("fake:nonexistent", "Model not found")
    print(f"\nRecovery result: {result}")
    
    print("\n" + "=" * 50)
    print("Incident Summary:")
    print(responder.get_incident_summary())
