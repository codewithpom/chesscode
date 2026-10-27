"""tests/test_job_registry.py — bounded job tracking (add/cleanup/archive)."""

import json
import os

from job_registry import JobRegistry


class FakeProc:
    def __init__(self, done=False, rc=0):
        self._done = done
        self._rc = rc
        self.closed = False

    def poll(self):
        return self._rc if self._done else None

    def terminate(self):
        """No-op terminate (for testing cancel)."""
        pass

    def kill(self):
        """No-op kill (for testing cancel with timeout)."""
        pass

    def wait(self, timeout=None):
        """Return the returncode (simulating process exit)."""
        return self._rc

    def close(self):
        """Mark as closed."""
        self.closed = True


def test_add_and_get_roundtrip():
    reg = JobRegistry(max_history=10, max_queue=10)
    assert reg.add("job1", {"title": "t"}) is True
    assert reg.get("job1") == {"title": "t"}
    assert reg.count() == 1


def test_add_rejects_when_queue_full():
    reg = JobRegistry(max_history=10, max_queue=2)
    assert reg.add("a", {}) is True
    assert reg.add("b", {}) is True
    assert reg.add("c", {}) is False
    assert reg.count() == 2


def test_update_only_affects_existing_job():
    reg = JobRegistry()
    reg.add("job1", {"title": "old"})
    reg.update("job1", {"title": "new"})
    assert reg.get("job1")["title"] == "new"

    reg.update("missing", {"title": "x"})  # no-op, must not raise
    assert reg.get("missing") is None


def test_remove_deletes_job():
    reg = JobRegistry()
    reg.add("job1", {})
    reg.remove("job1")
    assert reg.get("job1") is None
    assert reg.count() == 0


def test_get_queue_status_reports_utilization():
    reg = JobRegistry(max_queue=4)
    reg.add("a", {})
    status = reg.get_queue_status()
    assert status["total_jobs"] == 1
    assert status["max_queue"] == 4
    assert status["queue_full"] is False
    assert status["utilization_percent"] == 25


def test_cleanup_old_jobs_trims_oldest_by_timestamp():
    reg = JobRegistry(max_history=2, max_queue=10)
    reg._jobs = {"a": {}, "b": {}, "c": {}}
    reg._job_timestamps = {"a": 1.0, "b": 2.0, "c": 3.0}

    reg._cleanup_old_jobs()

    assert set(reg._jobs.keys()) == {"b", "c"}


def test_archive_job_writes_json(tmp_path, monkeypatch):
    import job_registry as jr
    monkeypatch.setattr(jr, "ARCHIVE_DIR", str(tmp_path))

    reg = JobRegistry()
    reg._jobs["job1"] = {"title": "My Video", "proc": FakeProc(done=True), "log_path": "logs/job1.log"}
    reg._job_timestamps["job1"] = 123.0

    reg._archive_job("job1")

    archive_file = tmp_path / "job1_meta.json"
    assert archive_file.exists()
    data = json.loads(archive_file.read_text())
    assert data["title"] == "My Video"
    assert data["status"] == "completed"


def test_cancel_running_job_terminates_and_marks_cancelled():
    """cancel() on a running job terminates the process and marks it cancelled."""
    reg = JobRegistry()

    # Create a running job (proc.poll() returns None)
    running_proc = FakeProc(done=False)
    reg.add("job1", {"proc": running_proc, "log_path": "logs/job1.log", "title": "Test"})

    # Cancel it
    result = reg.cancel("job1")

    # Should return the updated job data with status = "cancelled"
    assert result is not None
    assert result["status"] == "cancelled"

    # Job in registry should also be marked cancelled
    stored_job = reg.get("job1")
    assert stored_job is not None
    assert stored_job["status"] == "cancelled"


def test_cancel_nonexistent_job_returns_none():
    """cancel() on a non-existent job_id returns None (clean error)."""
    reg = JobRegistry()
    result = reg.cancel("unknown_job_id")
    assert result is None


def test_cancel_already_completed_job_marks_cancelled():
    """cancel() on an already-completed job still marks it cancelled without raising."""
    reg = JobRegistry()

    # Create a completed job (proc.poll() returns 0)
    completed_proc = FakeProc(done=True, rc=0)
    reg.add("job1", {"proc": completed_proc, "log_path": "logs/job1.log", "title": "Test"})

    # Cancel it
    result = reg.cancel("job1")

    # Should mark it cancelled without error
    assert result is not None
    assert result["status"] == "cancelled"


def test_cancel_job_without_proc_marks_cancelled():
    """cancel() on a job without a process still marks it cancelled."""
    reg = JobRegistry()

    # Create a job with no proc
    reg.add("job1", {"log_path": "logs/job1.log", "title": "Test"})

    # Cancel it
    result = reg.cancel("job1")

    # Should mark it cancelled without error
    assert result is not None
    assert result["status"] == "cancelled"


def test_cancel_cleans_up_output_directory(tmp_path):
    """cancel() cleans up the output directory for the job."""
    reg = JobRegistry()

    # Create output directory structure
    output_base = tmp_path / "output"
    output_base.mkdir()
    job_output = output_base / "job1_pgn"
    job_output.mkdir()
    (job_output / "dummy_file.txt").write_text("test content")

    # Create a running job
    running_proc = FakeProc(done=False)
    reg.add("job1", {"proc": running_proc, "log_path": "logs/job1.log", "title": "Test"})

    # Cancel with custom output_dir
    result = reg.cancel("job1", output_dir=str(output_base))

    # Output directory should be cleaned up
    assert not job_output.exists()
    # Job should be marked cancelled
    assert result["status"] == "cancelled"


def test_cancel_cleanup_survives_missing_output_dir(tmp_path):
    """cancel() never raises even if output directory doesn't exist."""
    reg = JobRegistry()

    # Use a path that doesn't exist
    nonexistent_output = tmp_path / "nonexistent" / "output"

    # Create a running job
    running_proc = FakeProc(done=False)
    reg.add("job1", {"proc": running_proc, "log_path": "logs/job1.log", "title": "Test"})

    # Cancel should succeed without raising
    result = reg.cancel("job1", output_dir=str(nonexistent_output))
    assert result is not None
    assert result["status"] == "cancelled"


def test_cancel_closes_log_file(tmp_path):
    """cancel() closes the job's log file handle if present."""
    reg = JobRegistry()

    log_file = tmp_path / "job1.log"
    log_f = open(log_file, "w")

    # Create a running job with log file
    running_proc = FakeProc(done=False)
    reg.add("job1", {"proc": running_proc, "log_path": str(log_file), "log_f": log_f, "title": "Test"})

    # Cancel it
    result = reg.cancel("job1")

    # Log file should be closed
    assert log_f.closed
    # Job should be marked cancelled
    assert result["status"] == "cancelled"


def test_cancel_returns_shallow_copy():
    """cancel() returns a shallow copy, not the live dict reference."""
    reg = JobRegistry()

    # Create a job
    running_proc = FakeProc(done=False)
    reg.add("job1", {"proc": running_proc, "log_path": "logs/job1.log", "title": "Test"})

    # Cancel and get the returned data
    result = reg.cancel("job1")

    # Modifying the returned dict should not affect the stored job
    result["title"] = "Modified"

    # Stored job should still have original title
    stored_job = reg.get("job1")
    assert stored_job["title"] == "Test"


def test_cancel_is_thread_safe():
    """cancel() is thread-safe (uses lock like other methods)."""
    import threading

    reg = JobRegistry()

    # Create multiple jobs
    for i in range(5):
        running_proc = FakeProc(done=False)
        reg.add(f"job{i}", {"proc": running_proc, "log_path": f"logs/job{i}.log", "title": f"Test {i}"})

    results = []
    errors = []

    def cancel_job(job_id):
        try:
            result = reg.cancel(job_id)
            results.append((job_id, result))
        except Exception as e:
            errors.append((job_id, e))

    # Cancel all jobs concurrently
    threads = [threading.Thread(target=cancel_job, args=(f"job{i}",)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All cancellations should succeed
    assert len(errors) == 0
    assert len(results) == 5
    for job_id, result in results:
        assert result is not None
        assert result["status"] == "cancelled"
