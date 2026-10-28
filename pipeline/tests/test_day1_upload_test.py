import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from chesscode import upload

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "day1_upload_test.py"
spec = importlib.util.spec_from_file_location("day1_upload_test", SCRIPT)
day1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(day1)


def test_dry_run_uses_upload_body_and_guard(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--publish-in-hours", "3", "--dry-run"])
    monkeypatch.setattr(day1.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(day1.imageio_ffmpeg, "get_ffmpeg_exe", lambda: "ffmpeg")
    seen = {}
    original = upload.build_body
    def capture(*args):
        body = original(*args)
        seen["body"] = body
        return body
    monkeypatch.setattr(day1, "build_body", capture)
    assert day1.main() == 0
    output = capsys.readouterr().out
    printed = json.loads(output[output.index("{", output.index("clip:")):])
    assert printed == seen["body"]


def test_dry_run_rejects_publish_time_before_rendering(monkeypatch):
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--publish-in-hours", "1", "--dry-run"])
    render = Mock(side_effect=AssertionError("should not render invalid publish time"))
    monkeypatch.setattr(day1.subprocess, "run", render)
    with pytest.raises(upload.UploadRefused):
        day1.main()
    render.assert_not_called()
