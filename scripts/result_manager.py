#!/usr/bin/env python3
"""
Result management script for git-based workflow result storage.
Organizes and commits workflow outputs to version control.
"""

import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

def run_git_command(command):
    """Execute git command and return result."""
    try:
        result = subprocess.run(
            ['git'] + command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e.stderr}")
        return None
    
def create_workflow_summary(result_dir, workflow_run, commit_sha):
    """Create a summary of workflow execution."""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "workflow_run": workflow_run,
        "commit_sha": commit_sha,
        "result_directory": str(result_dir),
        "files_created": []
    }
    
    result_dir = Path(result_dir)
    if result_dir.exists():
        for file_path in result_dir.rglob("*"):
            if file_path.is_file():
                relative = file_path.relative_to(result_dir)
                summary["files_created"].append(str(relative))
    
    return summary

def commit_results(result_dir, workflow_run, commit_sha):
    """Commit workflow results to git."""
    result_dir = Path(result_dir)
    
    summary = create_workflow_summary(result_dir, workflow_run, commit_sha)
    summary_file = result_dir / "workflow_summary.json"
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Created summary: {summary_file}")
    
    run_git_command(['add', str(result_dir)])
    
    commit_msg = f"Results from workflow run #{workflow_run}"
    result = run_git_command(['commit', '-m', commit_msg])
    
    if result is not None:
        print(f"Committed results for run #{workflow_run}")
        return True
    else:
        print("Failed to commit results")
        return False
    
def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage workflow results")
    parser.add_argument("--workflow-run", required=True, help="Workflow run number")
    parser.add_argument("--commit-sha", required=True, help="Commit SHA")
    parser.add_argument("--result-dir", required=True, help="Result directory path")
    
    args = parser.parse_args()
    
    result_dir = Path(args.result_dir)
    if not result_dir.exists():
        print(f"Result directory does not exist: {result_dir}")
        sys.exit(1)
    
    success = commit_results(result_dir, args.workflow_run, args.commit_sha)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()