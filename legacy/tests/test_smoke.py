"""tests/test_smoke.py — real end-to-end environment/dependency check.

Marked slow: excluded from the default `pytest -q` run (see pytest.ini
addopts). Run explicitly with `pytest -m slow` after touching dependencies,
Stockfish, ffmpeg, or TTS backend config.
"""

import os
import subprocess
import sys

import pytest


@pytest.mark.slow
def test_main_system_test_exits_cleanly():
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    result = subprocess.run(
        [sys.executable, "main.py", "--test"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
