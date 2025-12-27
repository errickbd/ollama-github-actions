#!/usr/bin/env python3
"""
SNS notification module for alerting on workflow incidents.
"""

import os
import sys
import subprocess
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from monitoring.correlation import get_correlation_id


class SNSNotifier:
    """Send alerts via AWS SNS."""
    
    def __init__(self, topic_arn=None):
        self.topic_arn = topic_arn or os.environ.get('SNS_TOPIC_ARN')
        self.region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        
        if self.topic_arn:
            print(f"SNS Notifier initialized: {self.topic_arn[:50]}...")
        else:
            print("SNS Notifier: No topic ARN configured")
    
    def send_alert(self, subject, message, severity='INFO'):
        """Send alert via SNS with correlation tracking."""
        if not self.topic_arn:
            print("SNS alert skipped: No topic ARN configured")
            return False
        
        corr_id = get_correlation_id()
        timestamp = datetime.now().isoformat()
        
        # SNS subject limit is 100 characters
        full_subject = f"[{severity}] {subject}"[:100]
        
        full_message = f"""
Correlation ID: {corr_id}
Severity: {severity}
Time: {timestamp}

{message}

---
Automated alert from AI Workflow System
"""
        
        try:
            result = subprocess.run(
                [
                    'aws', 'sns', 'publish',
                    '--topic-arn', self.topic_arn,
                    '--subject', full_subject,
                    '--message', full_message,
                    '--region', self.region
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            response = json.loads(result.stdout)
            print(f"SNS alert sent: {response.get('MessageId', 'unknown')}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"SNS notification failed: {e.stderr}")
            return False
        except FileNotFoundError:
            print("SNS notification failed: AWS CLI not installed")
            return False
        except Exception as e:
            print(f"SNS notification failed: {e}")
            return False


if __name__ == "__main__":
    from monitoring.correlation import generate_correlation_id
    generate_correlation_id()
    
    if len(sys.argv) > 1:
        topic_arn = sys.argv[1]
        notifier = SNSNotifier(topic_arn)
        
        print("\nSending test alert...")
        success = notifier.send_alert(
            "Test Alert",
            "This is a test message from the workflow system.",
            "INFO"
        )
        print(f"Alert sent: {success}")
    else:
        print("Usage: python sns_notifier.py <topic-arn>")
        print("\nExample:")
        print("  python sns_notifier.py arn:aws:sns:us-east-1:123456789:workflow-alerts")
