#!/usr/bin/env python3
"""
S3 integration module for cloud-based result storage.
Includes circuit breaker protection and local fallback.
"""

import os
import json
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cloud.circuit_breaker import CircuitBreaker
from monitoring.correlation import get_correlation_id


class S3Manager:
    """S3 integration with circuit breaker and local fallback."""

    def __init__(self, bucket_name=None):
        self.region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

        if bucket_name:
            self.bucket_name = bucket_name
        else:
            username = os.getenv('USER', 'workflow')
            self.bucket_name = f"ai-devops-results-{username}"
        
        # Circuit breaker for S3 operations
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, timeout_seconds=60)
        
        # Local fallback directory
        self.fallback_dir = Path('local_backup')

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

        corr_id = get_correlation_id()
        print(f"[{corr_id}] Uploading {local_path} to s3://{self.bucket_name}/{s3_key}")

        success, output = self.run_aws_command([
            's3', 'cp', str(local_path), f's3://{self.bucket_name}/{s3_key}',
            '--metadata', f'correlation_id={corr_id},timestamp={datetime.now().isoformat()}'
        ])

        if success:
            print(f"[{corr_id}] Upload successful: {s3_key}")
        else:
            print(f"[{corr_id}] Upload failed: {output}")

        return success

    def upload_directory(self, local_dir, s3_prefix):
        """Upload entire directory to S3."""
        local_dir = Path(local_dir)

        if not local_dir.exists():
            print(f"Local directory does not exist: {local_dir}")
            return False

        corr_id = get_correlation_id()
        print(f"[{corr_id}] Syncing {local_dir} to s3://{self.bucket_name}/{s3_prefix}")

        success, output = self.run_aws_command([
            's3', 'sync', str(local_dir), f's3://{self.bucket_name}/{s3_prefix}'
        ])

        if success:
            print(f"[{corr_id}] Sync successful: {s3_prefix}")
        else:
            print(f"[{corr_id}] Sync failed: {output}")

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
        corr_id = get_correlation_id()

        if metadata:
            metadata['s3_location'] = f"s3://{self.bucket_name}/{s3_key}"
            metadata['correlation_id'] = corr_id
            metadata_file = result_dir / "s3_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

        success = self.upload_directory(result_dir, s3_key)

        if success:
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            print(f"[{corr_id}] Results available at: {s3_url}")
            return s3_url

        return None

    def _save_to_fallback(self, local_path, s3_key):
        """Save to local fallback storage when S3 is unavailable."""
        corr_id = get_correlation_id()
        
        self.fallback_dir.mkdir(exist_ok=True)
        
        # Create path matching S3 key structure
        fallback_path = self.fallback_dir / s3_key
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(local_path, fallback_path)
        
        # Save metadata
        metadata = {
            'original_s3_key': s3_key,
            'correlation_id': corr_id,
            'timestamp': datetime.now().isoformat(),
            'reason': 'S3 circuit breaker open or upload failed',
            'bucket': self.bucket_name
        }
        metadata_path = Path(str(fallback_path) + '.meta.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"[{corr_id}] Saved to fallback: {fallback_path}")
        return str(fallback_path)

    def upload_with_protection(self, local_path, s3_key):
        """
        Upload with circuit breaker protection and local fallback.
        
        Args:
            local_path: Path to local file
            s3_key: Destination key in S3
        
        Returns:
            Storage location (S3 URL or local fallback path)
        """
        local_path = Path(local_path)
        corr_id = get_correlation_id()
        
        if not local_path.exists():
            print(f"[{corr_id}] File not found: {local_path}")
            return None
        
        # Check circuit breaker state
        if self.circuit_breaker.state.value == "open":
            print(f"[{corr_id}] Circuit breaker OPEN - using fallback storage")
            return self._save_to_fallback(local_path, s3_key)
        
        # Try S3 upload with circuit breaker
        try:
            def do_upload():
                success = self.upload_file(str(local_path), s3_key)
                if not success:
                    raise Exception("S3 upload returned False")
                return success
            
            self.circuit_breaker.call(do_upload)
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            print(f"[{corr_id}] Successfully uploaded to: {s3_url}")
            return s3_url
            
        except Exception as e:
            print(f"[{corr_id}] S3 upload failed: {e}")
            print(f"[{corr_id}] Circuit state: {self.circuit_breaker.state.value}")
            return self._save_to_fallback(local_path, s3_key)


if __name__ == "__main__":
    from monitoring.correlation import generate_correlation_id
    generate_correlation_id()
    
    s3 = S3Manager()
    
    print(f"Bucket name: {s3.bucket_name}")
    print(f"AWS configured: {s3.check_aws_configured()}")
    
    # Test protected upload
    print("\n" + "=" * 50)
    print("Testing protected upload")
    print("=" * 50)
    
    # Create a test file
    test_file = Path('test_upload.txt')
    test_file.write_text(f"Test content - {datetime.now().isoformat()}")
    
    location = s3.upload_with_protection(str(test_file), 'test/upload.txt')
    print(f"\nStored at: {location}")
    
    # Cleanup test file
    test_file.unlink()
    
    # Show fallback contents if used
    fallback_dir = Path('local_backup')
    if fallback_dir.exists():
        print("\nFallback directory contents:")
        for f in fallback_dir.rglob('*'):
            if f.is_file():
                print(f"  - {f}")
