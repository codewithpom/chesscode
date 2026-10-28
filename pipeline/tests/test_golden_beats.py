import json
from pathlib import Path
import pytest
from chesscode.config import load
from chesscode.stages.beats import detect, pace

ROOT = Path(__file__).parent / "golden"
EXPECTED = ROOT / "expected_beats"
FILES = sorted(EXPECTED.glob("*.json")) if EXPECTED.exists() else []

@pytest.mark.skipif(not FILES, reason="golden expected beats are supplied after review")
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_golden_beats(path):
    expected = json.loads(path.read_text(encoding="utf-8"))
    expected = expected["beats"] if isinstance(expected, dict) else expected
    analysis = ROOT / "analysis" / f"{path.stem}.json"
    assert analysis.is_file(), f"missing golden analysis: {analysis.name}"
    cfg=load("beats")
    rows=json.loads(analysis.read_text(encoding="utf-8"))
    actual=pace(detect(rows,cfg),None,cfg)
    assert [(b["type"],b["ply"],b["intensity"]) for b in actual] == [(b["type"],b["ply"],b["intensity"]) for b in expected]
