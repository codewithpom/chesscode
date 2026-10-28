import json
import shutil
import subprocess
from pathlib import Path

import pytest

from chesscode.context import Context, REPO_ROOT, StageError
from chesscode import tts
from chesscode.stages import voice


def test_files_named_by_segment(tmp_path, monkeypatch):
    ctx = Context("cc-2026-0001-en", tmp_path, REPO_ROOT, {}, "en", "studio")
    (tmp_path / "script.json").write_text(json.dumps({"segments": [
        {"kind": "hook", "text": "One two"}, {"kind": "ply", "text": "Three"}
    ]}))
    source = tmp_path / "cached.mp3"
    source.write_bytes(b"mp3")
    monkeypatch.setattr(tts, "synthesize", lambda *args: (source, [
        {"w": "word", "start_ms": 0, "end_ms": 100}
    ]))
    monkeypatch.setattr(voice, "_duration_ms", lambda path: 1000)

    voice.run(ctx)

    assert (tmp_path / "audio/en_seg-000.mp3").read_bytes() == b"mp3"
    assert (tmp_path / "audio/en_seg-001.mp3").is_file()
    rows = json.loads((tmp_path / "voice.json").read_text())
    assert [row["segment_id"] for row in rows] == ["seg-000", "seg-001"]


def test_duration_from_audio(tmp_path, monkeypatch):
    ctx = Context("cc-2026-0001-en", tmp_path, REPO_ROOT, {}, "en", "studio")
    (tmp_path / "script.json").write_text(json.dumps({"segments": [{"kind": "hook", "text": "Hi"}]}))
    source = tmp_path / "cached.mp3"
    source.write_bytes(b"mp3")
    monkeypatch.setattr(tts, "synthesize", lambda *args: (source, [{"w": "Hi", "start_ms": 0, "end_ms": 300}]))
    monkeypatch.setattr(voice, "_duration_ms", lambda path: 842)

    voice.run(ctx)

    assert json.loads((tmp_path / "voice.json").read_text())[0]["duration_ms"] == 842


def test_empty_words_raises(tmp_path, monkeypatch):
    ctx = Context("cc-2026-0001-en", tmp_path, REPO_ROOT, {}, "en", "studio")
    (tmp_path / "script.json").write_text(json.dumps({"segments": [{"kind": "hook", "text": "Hi"}]}))
    monkeypatch.setattr(tts, "synthesize", lambda *args: (tmp_path / "empty.mp3", []))

    with pytest.raises(StageError, match="word"):
        voice.run(ctx)

