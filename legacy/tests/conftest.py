"""conftest.py — shared fixtures for the ChessCode test suite."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class FakeProc:
    """Stand-in for subprocess.Popen — never spawns a real process."""

    def __init__(self, pid=4242, returncode=None):
        self.pid = pid
        self._returncode = returncode
        self.closed = False

    def poll(self):
        return self._returncode

    def terminate(self):
        """No-op terminate (for testing cancel)."""
        pass

    def kill(self):
        """No-op kill (for testing cancel with timeout)."""
        pass

    def wait(self, timeout=None):
        """Return the returncode (simulating process exit)."""
        return self._returncode

    def close(self):
        """Mark as closed."""
        self.closed = True


@pytest.fixture
def no_subprocess(monkeypatch):
    """Prevent MCP tool calls from spawning real main.py processes.

    Returns the list of captured Popen call kwargs (cmd is call.args[0][0]).
    """
    calls = []

    def _fake_popen(cmd, **kwargs):
        calls.append({"cmd": cmd, "kwargs": kwargs})
        return FakeProc()

    monkeypatch.setattr("subprocess.Popen", _fake_popen)
    return calls
