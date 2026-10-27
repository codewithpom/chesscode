"""job_registry.py — Manages the job registry with cleanup, limits, and resource protection.

This module provides bounded job tracking to prevent memory leaks and resource exhaustion:
- Automatic cleanup of old/completed jobs
- Max queue size enforcement
- Job history archival
- Thread-safe access
"""

import logging
import threading
import time
import json
import os
import subprocess
import shutil
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["JobRegistry", "JOB_HISTORY_LIMIT", "MAX_QUEUE_SIZE"]

# Configuration
JOB_HISTORY_LIMIT = 100  # Keep most recent 100 jobs
MAX_QUEUE_SIZE = 50      # Refuse new jobs if queue grows beyond this
ARCHIVE_DIR = "logs/archive"  # Directory for archived job metadata


class JobRegistry:
    """Thread-safe job registry with automatic cleanup and limits."""
    
    def __init__(self, max_history: int = JOB_HISTORY_LIMIT, max_queue: int = MAX_QUEUE_SIZE):
        """
        Initialize job registry.
        
        Args:
            max_history: Maximum number of jobs to keep in memory
            max_queue: Maximum queue size (reject jobs above this)
        """
        self.max_history = max_history
        self.max_queue = max_queue
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._job_timestamps: Dict[str, float] = {}  # Track job creation time
        self._cleanup_interval = 60  # Run cleanup every 60 seconds
        self._last_cleanup = time.time()
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    def add(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """
        Add a job to the registry.
        
        Args:
            job_id: Unique job identifier
            job_data: Job metadata dict
        
        Returns:
            True if added, False if queue is full
        """
        with self._lock:
            self._cleanup_if_needed()
            
            # Check queue size limit
            if len(self._jobs) >= self.max_queue:
                logger.warning(f"Job queue full ({len(self._jobs)} jobs). Rejecting new job {job_id}")
                return False
            
            self._jobs[job_id] = job_data
            self._job_timestamps[job_id] = time.time()
            logger.info(f"Job {job_id} added to registry. Queue size: {len(self._jobs)}")
            return True
    
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID (thread-safe)."""
        with self._lock:
            return self._jobs.get(job_id)
    
    def update(self, job_id: str, data: Dict[str, Any]) -> None:
        """Update job data (thread-safe)."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(data)
    
    def remove(self, job_id: str) -> None:
        """Remove job from registry (thread-safe)."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                if job_id in self._job_timestamps:
                    del self._job_timestamps[job_id]
                logger.debug(f"Job {job_id} removed from registry")
    
    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """Return copy of all jobs (thread-safe)."""
        with self._lock:
            return dict(self._jobs)

    def count(self) -> int:
        """Get current job count."""
        with self._lock:
            return len(self._jobs)

    # ── dict-like read access, so callers (e.g. job_monitor.py) can treat a
    # JobRegistry like the plain dict it replaced ──────────────────────────
    def values(self):
        return self.list_all().values()

    def items(self):
        return self.list_all().items()

    def __len__(self) -> int:
        return self.count()

    def __contains__(self, job_id: str) -> bool:
        return self.get(job_id) is not None
    
    def _cleanup_if_needed(self) -> None:
        """Run cleanup if interval has passed (must be called with lock held)."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = now
        self._cleanup_completed_jobs()
        self._cleanup_old_jobs()
    
    def _cleanup_completed_jobs(self) -> None:
        """Archive and remove completed jobs (must be called with lock held)."""
        completed = []
        for job_id, job_data in list(self._jobs.items()):
            proc = job_data.get("proc")
            if proc and proc.poll() is not None:  # Process finished
                completed.append(job_id)
        
        for job_id in completed:
            self._archive_job(job_id)
            del self._jobs[job_id]
            if job_id in self._job_timestamps:
                del self._job_timestamps[job_id]
            logger.debug(f"Archived completed job {job_id}")
    
    def _cleanup_old_jobs(self) -> None:
        """Remove oldest jobs if count exceeds max_history (must be called with lock held)."""
        if len(self._jobs) <= self.max_history:
            return
        
        # Sort by timestamp, remove oldest
        sorted_jobs = sorted(
            self._job_timestamps.items(),
            key=lambda x: x[1],
        )
        jobs_to_remove = len(self._jobs) - self.max_history
        for job_id, _ in sorted_jobs[:jobs_to_remove]:
            self._archive_job(job_id)
            del self._jobs[job_id]
            del self._job_timestamps[job_id]
            logger.debug(f"Archived old job {job_id} (history limit reached)")
    
    def _archive_job(self, job_id: str) -> None:
        """Save job metadata to archive (must be called with lock held)."""
        try:
            job_data = self._jobs.get(job_id, {})
            archive_file = os.path.join(ARCHIVE_DIR, f"{job_id}_meta.json")
            
            # Prepare archivable data (exclude process handles)
            archivable = {
                "job_id": job_id,
                "title": job_data.get("title", ""),
                "status": "completed" if job_data.get("proc", None) and job_data["proc"].poll() is not None else "running",
                "timestamp": self._job_timestamps.get(job_id),
                "log_path": job_data.get("log_path", ""),
            }
            
            with open(archive_file, "w", encoding="utf-8") as f:
                json.dump(archivable, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to archive job {job_id}: {e}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status for monitoring."""
        with self._lock:
            return {
                "total_jobs": len(self._jobs),
                "max_queue": self.max_queue,
                "queue_full": len(self._jobs) >= self.max_queue,
                "utilization_percent": int(100.0 * len(self._jobs) / self.max_queue),
            }

    def cancel(self, job_id: str, output_dir: str = "output") -> Optional[Dict[str, Any]]:
        """Terminate a running job's process, mark it cancelled, best-effort clean up
        partial output. Returns the job's data dict (with status updated), or None if
        job_id is unknown."""
        with self._lock:
            job_data = self._jobs.get(job_id)
            if job_data is None:
                return None

            # Terminate the process if it's still running
            proc = job_data.get("proc")
            if proc and proc.poll() is None:  # Process is still running
                try:
                    proc.terminate()
                    # Wait briefly for graceful termination
                    try:
                        proc.wait(timeout=5)
                        logger.debug(f"Job {job_id} process terminated gracefully")
                    except subprocess.TimeoutExpired:
                        # Escalate to kill if terminate didn't work
                        logger.warning(f"Job {job_id} did not terminate in time, killing")
                        proc.kill()
                        try:
                            proc.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            logger.warning(f"Job {job_id} could not be killed (still running)")
                except Exception as e:
                    logger.warning(f"Error terminating job {job_id}: {e}")

            # Mark job as cancelled
            job_data["status"] = "cancelled"

            # Close log file handle if present
            log_f = job_data.get("log_f")
            if log_f:
                try:
                    if not log_f.closed:
                        log_f.close()
                    logger.debug(f"Job {job_id} log file closed")
                except Exception as e:
                    logger.warning(f"Error closing log file for job {job_id}: {e}")

            # Best-effort cleanup of output directory
            try:
                output_path = os.path.join(output_dir, f"{job_id}_pgn")
                if os.path.exists(output_path):
                    shutil.rmtree(output_path, ignore_errors=True)
                    logger.debug(f"Job {job_id} output directory cleaned up")
            except Exception as e:
                logger.warning(f"Error cleaning up output for job {job_id}: {e}")

            # Return shallow copy of updated job data (defensive copy)
            return dict(job_data)
