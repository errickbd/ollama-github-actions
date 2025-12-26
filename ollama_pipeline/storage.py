#!/usr/bin/env python3
"""
Storage module for Ollama Pipeline.
Centralizes directory management and git operations.
"""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


class DirectoryManager:
    """Manages timestamped directories for workflow results."""
    
    def __init__(self, base_dir="results"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    def create_timestamped_dir(self, prefix="workflow"):
        """Create a new timestamped directory."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        dir_name = f"{prefix}-{timestamp}"
        dir_path = self.base_dir / dir_name
        dir_path.mkdir(exist_ok=True)
        
        print(f"📁 Created directory: {dir_path}")
        return dir_path
    
    def get_latest_dir(self, prefix="workflow"):
        """Get the most recent directory matching prefix."""
        pattern = f"{prefix}-*"
        matching_dirs = list(self.base_dir.glob(pattern))
        
        if not matching_dirs:
            return None
        
        latest = max(matching_dirs, key=lambda p: p.stat().st_mtime)
        return latest
    
    def list_directories(self, prefix="workflow", limit=10):
        """List recent directories matching prefix."""
        pattern = f"{prefix}-*"
        matching_dirs = list(self.base_dir.glob(pattern))
        
        sorted_dirs = sorted(
            matching_dirs,
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        return sorted_dirs[:limit]
    
    def cleanup_old_directories(self, prefix="workflow", keep=5):
        """Remove old directories, keeping only the most recent."""
        all_dirs = self.list_directories(prefix, limit=100)
        
        if len(all_dirs) <= keep:
            print(f"Only {len(all_dirs)} directories found, no cleanup needed")
            return 0
        
        to_remove = all_dirs[keep:]
        for dir_path in to_remove:
            print(f"🗑️  Removing old directory: {dir_path}")
            shutil.rmtree(dir_path)
        
        print(f"✅ Cleaned up {len(to_remove)} old directories")
        return len(to_remove)


def run_git_command(command):
    """
    Execute git command and return result.
    
    Args:
        command: List of git command arguments (without 'git')
    
    Returns:
        stdout string if successful, None if failed
    """
    try:
        result = subprocess.run(
            ['git'] + command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Git command failed: {e.stderr}")
        return None


def checkout_results_branch(branch_name="results"):
    """
    Checkout or create the results branch.
    
    Args:
        branch_name: Name of the results branch
    
    Returns:
        True if successful, False otherwise
    """
    # Check if branch exists
    result = run_git_command(['branch', '--list', branch_name])
    
    if result and branch_name in result:
        # Branch exists, checkout
        print(f"📂 Checking out existing branch: {branch_name}")
        run_git_command(['checkout', branch_name])
    else:
        # Create new branch
        print(f"📂 Creating new branch: {branch_name}")
        run_git_command(['checkout', '-b', branch_name])
    
    return True


def commit_results(result_dir, metadata=None):
    """
    Commit workflow results to git.
    
    Args:
        result_dir: Path to the result directory
        metadata: Optional dictionary of metadata to include
    
    Returns:
        True if successful, False otherwise
    """
    result_dir = Path(result_dir)
    
    # Create workflow summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "result_directory": str(result_dir),
        "files_created": []
    }
    
    # Add custom metadata
    if metadata:
        summary.update(metadata)
    
    # List files in result directory
    if result_dir.exists():
        for file_path in result_dir.rglob("*"):
            if file_path.is_file():
                relative = file_path.relative_to(result_dir)
                summary["files_created"].append(str(relative))
    
    # Write summary file
    summary_file = result_dir / "workflow_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"📄 Created summary: {summary_file}")
    
    # Git operations
    run_git_command(['add', str(result_dir)])
    
    commit_msg = f"Results from {result_dir.name}"
    result = run_git_command(['commit', '-m', commit_msg])
    
    if result is not None:
        print(f"✅ Committed results: {commit_msg}")
        return True
    else:
        print("⚠️  No changes to commit or commit failed")
        return False


class ResultStorage:
    """
    Combines directory management and git operations for result storage.
    """
    
    def __init__(self, base_dir="results"):
        """
        Initialize storage with base directory.
        
        Args:
            base_dir: Base directory for storing results
        """
        self.dir_manager = DirectoryManager(base_dir)
        self.base_dir = Path(base_dir)
        self.current_dir = None
        print(f"💾 ResultStorage initialized: {base_dir}")
    
    def create_run_directory(self, run_id):
        """
        Create a timestamped directory for a workflow run.
        
        Args:
            run_id: Workflow run identifier (e.g., run number)
        
        Returns:
            Path to the created directory
        """
        prefix = f"run-{run_id}"
        self.current_dir = self.dir_manager.create_timestamped_dir(prefix)
        return self.current_dir
    
    def save_analysis(self, filename, content, metadata=None):
        """
        Save analysis result to current directory.
        
        Args:
            filename: Name of the file to create
            content: Content to write
            metadata: Optional metadata dictionary
        
        Returns:
            Path to the saved file
        """
        if not self.current_dir:
            raise ValueError("No current directory. Call create_run_directory first.")
        
        file_path = self.current_dir / filename
        
        # Write content
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"💾 Saved: {file_path}")
        
        # Save metadata if provided
        if metadata:
            meta_path = self.current_dir / f"{filename}.meta.json"
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        return file_path
    
    def save_metadata(self, metadata):
        """
        Save metadata file to current directory.
        
        Args:
            metadata: Dictionary of metadata
        
        Returns:
            Path to metadata file
        """
        if not self.current_dir:
            raise ValueError("No current directory. Call create_run_directory first.")
        
        file_path = self.current_dir / "metadata.txt"
        
        with open(file_path, 'w') as f:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
        
        print(f"💾 Saved metadata: {file_path}")
        return file_path
    
    def commit_all(self, workflow_run=None, commit_sha=None):
        """
        Commit all pending results to git.
        
        Args:
            workflow_run: Optional workflow run number
            commit_sha: Optional commit SHA
        
        Returns:
            True if successful, False otherwise
        """
        if not self.current_dir:
            print("⚠️  No current directory to commit")
            return False
        
        metadata = {}
        if workflow_run:
            metadata['workflow_run'] = workflow_run
        if commit_sha:
            metadata['commit_sha'] = commit_sha
        
        return commit_results(self.current_dir, metadata)
    
    def get_all_summaries(self):
        """
        Get all workflow summaries from results directory.
        
        Returns:
            List of summary dictionaries
        """
        summaries = []
        
        for summary_file in self.base_dir.rglob("workflow_summary.json"):
            try:
                with open(summary_file) as f:
                    summaries.append(json.load(f))
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Failed to read {summary_file}: {e}")
        
        # Sort by timestamp, newest first
        summaries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return summaries
    
    def cleanup(self, keep=5):
        """
        Clean up old result directories.
        
        Args:
            keep: Number of recent directories to keep
        
        Returns:
            Number of directories removed
        """
        return self.dir_manager.cleanup_old_directories(prefix="run", keep=keep)
