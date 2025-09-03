"""
File Cleanup Utilities for DBI Operations Hub
Handles scheduled cleanup of temporary files and old uploads.
"""
import os
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
from .logging_config import get_logger, LoggerMixin
from .exceptions import FileOperationError

logger = get_logger(__name__)


class FileCleanupManager(LoggerMixin):
    """Manages cleanup of temporary files and directories"""
    
    def __init__(self, cleanup_interval_hours: int = 24):
        """
        Initialize file cleanup manager
        
        Args:
            cleanup_interval_hours: How often to run cleanup (in hours)
        """
        self.cleanup_interval_hours = cleanup_interval_hours
        self.cleanup_thread = None
        self.running = False
        
        # Default cleanup rules (file age in hours)
        self.cleanup_rules = {
            'uploads': 48,      # Keep upload files for 48 hours
            'staging': 24,      # Keep staging files for 24 hours  
            'logs': 168,        # Keep log files for 1 week
            'temp': 6,          # Keep temp files for 6 hours
        }
    
    def add_cleanup_rule(self, directory: str, max_age_hours: int):
        """Add or update a cleanup rule"""
        self.cleanup_rules[directory] = max_age_hours
        self.log_operation(f"Added cleanup rule: {directory} -> {max_age_hours} hours")
    
    def start_scheduled_cleanup(self):
        """Start the scheduled cleanup process in a background thread"""
        if self.running:
            self.logger.warning("Cleanup scheduler already running")
            return
        
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        self.log_operation("Started scheduled file cleanup service")
    
    def stop_scheduled_cleanup(self):
        """Stop the scheduled cleanup process"""
        self.running = False
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        self.log_operation("Stopped scheduled file cleanup service")
    
    def _cleanup_loop(self):
        """Main cleanup loop that runs in background thread"""
        while self.running:
            try:
                self.run_cleanup()
            except Exception as e:
                self.log_error(f"Error during scheduled cleanup: {str(e)}", operation="scheduled_cleanup")
            
            # Sleep for the specified interval
            sleep_seconds = self.cleanup_interval_hours * 3600
            for _ in range(sleep_seconds):
                if not self.running:
                    break
                time.sleep(1)
    
    def run_cleanup(self) -> Dict[str, int]:
        """
        Run file cleanup based on configured rules
        
        Returns:
            Dictionary with cleanup statistics
        """
        cleanup_stats = {
            'files_deleted': 0,
            'directories_cleaned': 0,
            'bytes_freed': 0,
            'errors': 0
        }
        
        self.log_operation("Starting file cleanup process", operation="run_cleanup")
        
        for directory, max_age_hours in self.cleanup_rules.items():
            try:
                dir_stats = self._cleanup_directory(directory, max_age_hours)
                cleanup_stats['files_deleted'] += dir_stats['files_deleted']
                cleanup_stats['bytes_freed'] += dir_stats['bytes_freed']
                cleanup_stats['directories_cleaned'] += 1
            except Exception as e:
                cleanup_stats['errors'] += 1
                self.log_error(
                    f"Error cleaning directory {directory}: {str(e)}", 
                    operation="cleanup_directory",
                    directory=directory
                )
        
        self.log_operation(
            f"Cleanup completed: deleted {cleanup_stats['files_deleted']} files, "
            f"freed {cleanup_stats['bytes_freed']} bytes",
            operation="run_cleanup",
            **cleanup_stats
        )
        
        return cleanup_stats
    
    def _cleanup_directory(self, directory: str, max_age_hours: int) -> Dict[str, int]:
        """
        Clean up files in a specific directory
        
        Args:
            directory: Directory to clean
            max_age_hours: Maximum age of files to keep
            
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {'files_deleted': 0, 'bytes_freed': 0}
        
        if not os.path.exists(directory):
            return stats
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cutoff_timestamp = cutoff_time.timestamp()
        
        directory_path = Path(directory)
        
        # Clean files in the directory and all subdirectories
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                try:
                    file_stat = file_path.stat()
                    
                    # Check if file is older than cutoff
                    if file_stat.st_mtime < cutoff_timestamp:
                        file_size = file_stat.st_size
                        file_path.unlink()
                        stats['files_deleted'] += 1
                        stats['bytes_freed'] += file_size
                        
                        self.logger.debug(
                            f"Deleted old file: {file_path}",
                            extra={
                                'operation': 'delete_old_file',
                                'file_path': str(file_path),
                                'file_age_hours': (time.time() - file_stat.st_mtime) / 3600,
                                'file_size': file_size
                            }
                        )
                
                except (OSError, IOError) as e:
                    self.log_error(
                        f"Failed to delete file {file_path}: {str(e)}",
                        operation="delete_file",
                        file_path=str(file_path)
                    )
        
        # Clean up empty directories
        self._cleanup_empty_directories(directory_path)
        
        return stats
    
    def _cleanup_empty_directories(self, directory_path: Path):
        """Remove empty directories recursively"""
        try:
            for dir_path in sorted(directory_path.rglob('*'), key=lambda p: len(p.parts), reverse=True):
                if dir_path.is_dir() and dir_path != directory_path:
                    try:
                        # Only remove if empty
                        dir_path.rmdir()
                        self.logger.debug(f"Removed empty directory: {dir_path}")
                    except OSError:
                        # Directory not empty, continue
                        pass
        except Exception as e:
            self.log_error(f"Error cleaning empty directories: {str(e)}")
    
    def cleanup_specific_files(self, file_patterns: List[str]) -> int:
        """
        Clean up specific files matching patterns
        
        Args:
            file_patterns: List of file patterns to delete
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        
        for pattern in file_patterns:
            try:
                # Use pathlib to find matching files
                for file_path in Path('.').glob(pattern):
                    if file_path.is_file():
                        file_path.unlink()
                        deleted_count += 1
                        self.log_operation(
                            f"Deleted file: {file_path}",
                            operation="cleanup_specific_file",
                            file_path=str(file_path)
                        )
            except Exception as e:
                self.log_error(
                    f"Error deleting files matching pattern {pattern}: {str(e)}",
                    operation="cleanup_pattern",
                    pattern=pattern
                )
        
        return deleted_count
    
    def get_directory_size(self, directory: str) -> Dict[str, int]:
        """
        Get directory size and file count
        
        Args:
            directory: Directory to analyze
            
        Returns:
            Dictionary with size and count information
        """
        info = {'total_size': 0, 'file_count': 0}
        
        if not os.path.exists(directory):
            return info
        
        directory_path = Path(directory)
        
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                try:
                    info['file_count'] += 1
                    info['total_size'] += file_path.stat().st_size
                except (OSError, IOError):
                    pass
        
        return info


# Global cleanup manager instance
cleanup_manager = FileCleanupManager()


def start_file_cleanup_service(cleanup_interval_hours: int = 24):
    """Start the file cleanup service"""
    cleanup_manager.cleanup_interval_hours = cleanup_interval_hours
    cleanup_manager.start_scheduled_cleanup()


def stop_file_cleanup_service():
    """Stop the file cleanup service"""
    cleanup_manager.stop_scheduled_cleanup()


def run_manual_cleanup() -> Dict[str, int]:
    """Run manual file cleanup and return statistics"""
    return cleanup_manager.run_cleanup()


def cleanup_temp_files() -> int:
    """Clean up temporary files immediately"""
    temp_patterns = [
        'uploads/*/temp_*',
        'staging/*/*temp*',
        '*.tmp',
        'logs/*.log.*'  # Rotated log files
    ]
    return cleanup_manager.cleanup_specific_files(temp_patterns)
