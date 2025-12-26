#!/usr/bin/env python3
"""
Directory management utility for organizing workflow results.
Provides timestamped directory creation and management.
"""

import shutil
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
        
        print(f"Created directory: {dir_path}")
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
                print(f"Removing old directory: {dir_path}")
                shutil.rmtree(dir_path)
            
            print(f"Cleaned up {len(to_remove)} old directories")
            return len(to_remove)

if __name__ == "__main__":
    dm = DirectoryManager()
    new_dir = dm.create_timestamped_dir("test-run")
    print(f"Created: {new_dir}")
    
    recent = dm.list_directories()
    print(f"Recent directories: {[d.name for d in recent]}")