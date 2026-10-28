"""Golden regression: classify + beats on 10 real games must match the hand-reviewed beats.

Expected files were reviewed by the main session (audits/golden-run-2.txt). Regenerate only
through a reviewed commit.
"""
import json
import shutil
from pathlib import Path

import pytest

from chesscode.context import Context
from chesscode.stages import beats, classify

ROOT = Path(__file__).parent / "golden"
EXPECTED = ROOT / "expected_beats"
FILES = sorted(EXPECTED.glob("*.json")) if EXPECTED.exists() else []
REPO = Path(__file__).resolve().parents[2]


def run_golden(name: str, tmp_path: Path) -> list[dict]:
    shutil.copy(ROOT / "analysis" / f"{name}.json", tmp_path / "analysis.json")
    shutil.copy(ROOT / "pgn" / f"{name}.pgn", tmp_path / "game.pgn")
    ctx = Context(video_id="cc-2026-0001-en", spec_dir=tmp_path, repo_root=REPO, game={}, language="en", template="studio")
    classify.run(ctx)
    beats.run(ctx)
    out = json.loads((tmp_path / "beats.json").read_text(encoding="utf-8"))
    return out["beats"] if isinstance(out, dict) else out


@pytest.mark.skipif(not FILES, reason="golden expected beats are supplied after review")
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_golden_beats(path, tmp_path):
    expected = json.loads(path.read_text(encoding="utf-8"))
    actual = run_golden(path.stem, tmp_path)
    assert [(b["type"], b["ply"], b["intensity"], b["pose"]) for b in actual] == \
           [(b["type"], b["ply"], b["intensity"], b["pose"]) for b in expected]
