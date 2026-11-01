"""Exercise the actual upload content through emit before generating remote audio."""
import importlib
import json
from dataclasses import replace
from unittest.mock import Mock

import pytest

from chesscode.runner import _context
from chesscode.stages import emit, metadata, script, timeline


@pytest.mark.parametrize("video", [
    "cc-2026-0005-hi", "cc-2026-0006-en", "cc-2026-0006-hi",
    "cc-2026-0007-en", "cc-2026-0007-hi",
])
def test_upload_content_reaches_valid_spec_without_network_or_synthesis(tmp_path, monkeypatch, video):
    ctx = replace(_context(video), spec_dir=tmp_path)
    assert ctx.game["source"] == "local"
    monkeypatch.setattr(metadata.llm, "provider", lambda: "offline")
    for stage in ("select", "fetch", "analyze", "classify", "beats"):
        importlib.import_module(f"chesscode.stages.{stage}").run(ctx)
    output = script._replay(ctx, ctx.repo_root / "content/scripts" / f"{video}.json")
    (tmp_path / "script.json").write_text(json.dumps(output), encoding="utf-8")
    rate = 140 if ctx.language == "hi" else 150
    voice = []
    for index, segment in enumerate(output["segments"]):
        words = segment["text"].split()
        voice.append({
            "segment_id": f"seg-{index:03d}", "audio": f"audio/{ctx.language}_seg-{index:03d}.mp3",
            "duration_ms": round(len(words) * 60000 / rate),
            "words": [{"w": word, "start_ms": round(i * 60000 / rate),
                       "end_ms": round((i + 1) * 60000 / rate)} for i, word in enumerate(words)],
        })
    (tmp_path / "voice.json").write_text(json.dumps(voice), encoding="utf-8")
    timeline.run(ctx)
    metadata.run(ctx)
    monkeypatch.setattr(emit, "prepare_music", Mock(return_value={
        "track": "music/test.mp3", "volume": 0.12, "duck_under_voice": 0.06,
    }))
    spec = emit.assemble(ctx)
    emit.validate(spec)
    for fact in (spec["game"]["white"]["name"], spec["game"]["black"]["name"], spec["game"]["date"], spec["game"]["result"]):
        assert fact in spec["youtube"]["description"]
