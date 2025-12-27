#!/usr/bin/env python3
"""
S3 integration module for cloud-based result storage.
Provides simple S3 upload and management capabilities.
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

class S3Manager:
    """Simple S3 integration for workflow result storage."""
    
    def __init__(self, bucket_name=None):
        self.region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        if bucket_name:
            self.bucket_name = bucket_name
        else:
            username = os.getenv('USER', 'workflow')
            self.bucket_name = f"ai-devops-results-{username}"
    
    def run_aws_command(self, command):
        """Execute AWS CLI command and return result."""
        try:
            result = subprocess.run(
                ['aws'] + command,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip()
        except FileNotFoundError:
            return False, "AWS CLI not installed"
        
    def check_aws_configured(self):
        """Check if AWS credentials are configured."""
        success, output = self.run_aws_command(['sts', 'get-caller-identity'])
        return success
    
    def check_bucket_exists(self):
        """Check if the S3 bucket exists."""
        success, output = self.run_aws_command(['s3', 'ls', f's3://{self.bucket_name}'])
        return success
    
    def create_bucket_if_needed(self):
        """Create S3 bucket if it doesn't exist."""
        if not self.check_aws_configured():
            print("AWS credentials not configured")
            return False
        
        if self.check_bucket_exists():
            print(f"Bucket {self.bucket_name} already exists")
            return True
        
        print(f"Creating bucket {self.bucket_name}")
        success, output = self.run_aws_command([
            's3', 'mb', f's3://{self.bucket_name}',
            '--region', self.region
        ])
        
        if success:
            print(f"Successfully created bucket {self.bucket_name}")
        else:
            print(f"Failed to create bucket: {output}")
        
        return success
    
    def upload_file(self, local_path, s3_key):
        """Upload a single file to S3."""
        local_path = Path(local_path)
        
        if not local_path.exists():
            print(f"Local file does not exist: {local_path}")
            return False
        
        print(f"Uploading {local_path} to s3://{self.bucket_name}/{s3_key}")
        
        success, output = self.run_aws_command([
            's3', 'cp', str(local_path), f's3://{self.bucket_name}/{s3_key}'
        ])
        
        if success:
            print(f"Upload successful: {s3_key}")
        else:
            print(f"Upload failed: {output}")
        
        return success
    
    def upload_directory(self, local_dir, s3_prefix):
        """Upload entire directory to S3."""
        local_dir = Path(local_dir)
        
        if not local_dir.exists():
            print(f"Local directory does not exist: {local_dir}")
            return False
        
        print(f"Syncing {local_dir} to s3://{self.bucket_name}/{s3_prefix}")
        
        success, output = self.run_aws_command([
            's3', 'sync', str(local_dir), f's3://{self.bucket_name}/{s3_prefix}'
        ])
        
        if success:
            print(f"Sync successful: {s3_prefix}")
        else:
            print(f"Sync failed: {output}")
        
        return success
    
    def generate_workflow_key(self, workflow_run):
        """Generate organized S3 key for workflow results."""
        timestamp = datetime.now()
        date_str = timestamp.strftime("%Y/%m/%d")
        time_str = timestamp.strftime("%H-%M-%S")
        return f"results/{date_str}/run-{workflow_run}-{time_str}"
    
    def upload_workflow_results(self, result_dir, workflow_run, metadata=None):
        """Upload complete workflow results with metadata."""
        result_dir = Path(result_dir)
        s3_key = self.generate_workflow_key(workflow_run)
        
        if metadata:
            metadata['s3_location'] = f"s3://{self.bucket_name}/{s3_key}"
            metadata_file = result_dir / "s3_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        success = self.upload_directory(result_dir, s3_key)
        
        if success:
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            print(f"Results available at: {s3_url}")
            return s3_url
        
        return None
    
if __name__ == "__main__":
    s3 = S3Manager()
    
    print(f"Bucket name: {s3.bucket_name}")
    print(f"AWS configured: {s3.check_aws_configured()}")
    
    if s3.check_aws_configured():
        print(f"Bucket exists: {s3.check_bucket_exists()}")