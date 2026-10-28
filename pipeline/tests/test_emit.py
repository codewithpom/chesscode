import copy
import json
from pathlib import Path
import pytest
from chesscode.context import Context, StageError
from chesscode.stages import emit

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/"spec/fixtures/cc-2026-0001-en/video_spec.json"

def test_fixture_validates():
    emit.validate(json.loads(FIXTURE.read_text(encoding="utf-8")))

def test_broken_spec_error_is_readable():
    spec=json.loads(FIXTURE.read_text(encoding="utf-8")); spec["video_id"]="wrong"
    with pytest.raises(StageError,match="video_id"): emit.validate(spec)

def test_cross_field_overlap_rejected():
    spec=json.loads(FIXTURE.read_text(encoding="utf-8")); spec["narration"][1]["start_ms"]=spec["narration"][0]["start_ms"]
    with pytest.raises(StageError,match="narration"): emit.validate(spec)

def test_not_written_when_invalid(tmp_path):
    data=json.loads(FIXTURE.read_text(encoding="utf-8")); data["video_id"]="wrong"
    specdir=tmp_path/"spec"; specdir.mkdir()
    parts={"game.json":data,"classified.json":data["plies"],"beats.json":data["beats"],"script.json":{"segments":[],"mascot_lines":{}},"timeline.json":{"narration":data["narration"],"beats":data["beats"],"chapters":data["chapters"],"duration_ms":data["duration_ms"],"plies_show_at":{}},"metadata.json":data["youtube"]}
    for name,value in parts.items(): (specdir/name).write_text(json.dumps(value))
    with pytest.raises(StageError): emit.run(Context("wrong",specdir,ROOT,{},"en","studio"))
    assert not (specdir/"video_spec.json").exists()
