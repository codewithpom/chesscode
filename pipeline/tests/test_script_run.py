"""script.run with a fake model: SAN guard on every final text, idempotency, Hindi prompt, line bank."""
import json
import shutil
import sqlite3
from pathlib import Path

import pytest
import yaml

from chesscode.context import Context, StageError
from chesscode.stages import script

ROOT = Path(__file__).resolve().parents[2]
START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
AFTER = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
GOOD = " ".join(["Knight f3 attacks the e5 pawn"] * 10)  # 60 words


def setup_run(tmp_path, monkeypatch, language="en", bank=True):
    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "config", repo / "config")
    if bank:
        (repo / "content/lines").mkdir(parents=True)
        (repo / f"content/lines/{language}.yaml").write_text(yaml.safe_dump({"blunder": ["Bank line one.", "Bank line two."], "mistake": ["Mistake bank one."]}))
    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "game.json").write_text("{}")
    (spec / "classified.json").write_text(json.dumps([{"ply": 1, "san": "e4", "uci": "e2e4", "fen_before": START, "fen_after": AFTER, "before": [], "after": []}]))
    (spec / "beats.json").write_text(json.dumps([{"beat_id": "b-01", "type": "blunder", "ply": 1, "intensity": 2, "priority": 0, "pose": "facepalm"},
                                                 {"beat_id": "b-02", "type": "mistake", "ply": 1, "intensity": 1, "priority": 9, "pose": "side_eye"}]))
    monkeypatch.setattr(script, "ensure_specific", lambda output, *args: output)
    return Context("cc-2026-5001-" + language, spec, repo, {}, language, "shorts")


def model(outputs, systems=None):
    calls = []

    def fake(key, system, user, schema):
        if key == "checks":
            return {"ok": True}
        calls.append(user)
        if systems is not None:
            systems.append(system)
        return outputs[min(len(calls) - 1, len(outputs) - 1)]

    return fake, calls


def out(text=GOOD, titles=("A quiet move", "Another title", "Third title"), hook="A hook.", lines=None, segments=None, **extra):
    return {"segments": segments or [{"kind": "cold_open", "ply": None, "text": text}, {"kind": "ply", "ply": 1, "text": text}],
            "mascot_lines": lines or {"b-01": "Oops again."}, "titles": list(titles), "hook": hook,
            "player_facts": {"white": "White fact.", "black": "Black fact."}, "cold_open_hook": "A hook line", "thumbnail_text": "Quiet move",
            "key_moment_labels": {"b-01": "The slip"}, **extra}


def test_unknown_san_in_titles_and_hook_is_caught(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    bad = out(titles=("Qh5 changes everything", "Another title", "Third title"), hook="Then Bxd5 happens.")
    fake, calls = model([bad, out(), out()])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    final = json.loads((ctx.spec_dir / "script.json").read_text())
    assert final["titles"][0] == "A quiet move" and final["hook"] == "A hook."


def test_san_that_only_appears_after_length_regeneration_is_caught(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    short = out(text="word " * 5)  # too short: forces whole-output regeneration, which carries a bad move
    fake, calls = model([short, out(text=GOOD + " Qh5"), out()])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    assert "Qh5" not in (ctx.spec_dir / "script.json").read_text()


def test_regeneration_returning_one_segment_does_not_raise(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    bad = out(segments=[{"kind": "cold_open", "ply": None, "text": GOOD}, {"kind": "ply", "ply": 1, "text": GOOD + " Qh5"}])
    one = {**out(), "segments": [{"kind": "ply", "ply": 1, "text": GOOD}]}
    fake, calls = model([bad, one])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    final = json.loads((ctx.spec_dir / "script.json").read_text())
    assert [s["kind"] for s in final["segments"]] == ["cold_open", "ply"] and final["segments"][1]["ply"] == 1
    assert "Qh5" not in final["segments"][1]["text"]


def test_persistent_unknown_san_stops_with_reason(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    fake, _ = model([out(hook="Always Qh5.")])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    with pytest.raises(StageError, match="unknown SAN"):
        script.run(ctx)


def test_mascot_line_with_unknown_san_falls_back_to_bank(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    fake, _ = model([out(lines={"b-01": "Qh5 is brave."})])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    assert json.loads((ctx.spec_dir / "script.json").read_text())["mascot_lines"]["b-01"] == "Bank line one."


def test_rerun_keeps_its_own_lines_and_one_history_row(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    fake, _ = model([out()])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    script.run(ctx)
    assert json.loads((ctx.spec_dir / "script.json").read_text())["mascot_lines"]["b-01"] == "Oops again."
    with sqlite3.connect(ctx.repo_root / "data/line_history.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM line_history WHERE video_id=?", (ctx.video_id,)).fetchone()[0] == 1


def test_missing_line_bank_is_a_clear_stage_error(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch, bank=False)
    fake, _ = model([out(lines={"b-01": "way too many words for a mascot line here ok"})])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    with pytest.raises(StageError, match=r"cc-2026-5001-en \[script\]: line bank missing"):
        script.run(ctx)


def test_exhausted_line_bank_error_names_the_video(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    (ctx.repo_root / "content/lines/en.yaml").write_text(yaml.safe_dump({"blunder": []}))
    fake, _ = model([out(lines={"b-01": "way too many words for a mascot line here ok"})])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    with pytest.raises(StageError, match=r"cc-2026-5001-en \[script\]: no unused en fallback"):
        script.run(ctx)


def test_hindi_prompt_keeps_chess_terms_in_english(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch, language="hi")
    systems = []
    fake, _ = model([out()], systems)
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    assert "Do not translate or use any English script" not in systems[0]
    assert "Keep chess terms" in systems[0] and "never translate an English script" in systems[0]


def test_prompt_is_hashed_and_asks_for_ply_segments(tmp_path):
    from chesscode import runner
    repo = tmp_path / "repo"
    prompt = repo / "pipeline/chesscode/prompts/script_system.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("one")
    ctx = Context("cc-2026-0001-en", tmp_path / "spec", repo, {}, "en", "studio")
    before = runner._input_hash(ctx, script.INPUTS)
    prompt.write_text("two")
    assert runner._input_hash(ctx, script.INPUTS) != before
    assert 'kind "ply"' in (ROOT / "pipeline/chesscode/prompts/script_system.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("field,bad", [
    ("player_facts", {"white": "Played Qh5 early.", "black": "Black fact."}),
    ("cold_open_hook", "Qh5 shocks all"),
    ("thumbnail_text", "Qh5 sac"),
    ("key_moment_labels", {"b-01": "Then Bxd5"}),
])
def test_unknown_san_in_the_new_text_fields_is_regenerated(tmp_path, monkeypatch, field, bad):
    ctx = setup_run(tmp_path, monkeypatch)
    fake, calls = model([out(**{field: bad}), out()])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    final = json.loads((ctx.spec_dir / "script.json").read_text())
    assert final[field] == out()[field]
    assert len(calls) == 2


def test_persistent_unknown_san_in_a_fact_stops(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    fake, _ = model([out(player_facts={"white": "Always Qh5.", "black": "Black fact."})])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    with pytest.raises(StageError, match="unknown SAN.*player_facts"):
        script.run(ctx)


def test_schema_bounds_for_the_new_fields():
    import jsonschema
    jsonschema.validate(out(), script.SCHEMA)
    for field, bad in [("cold_open_hook", "x" * 61), ("thumbnail_text", "one two three four five"), ("key_moment_labels", {"b-01": "x" * 41}),
                       ("player_facts", {"white": "x" * 121, "black": "ok"}), ("player_facts", {"white": "ok"})]:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(out(**{field: bad}), script.SCHEMA)
    for field in ("player_facts", "cold_open_hook", "thumbnail_text", "key_moment_labels"):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({k: v for k, v in out().items() if k != field}, script.SCHEMA)


def test_thumbnail_text_repeating_a_title_stops(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    fake, _ = model([out(thumbnail_text="a QUIET move")])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    with pytest.raises(StageError, match="thumbnail_text"):
        script.run(ctx)


def test_long_form_needs_a_label_for_every_intensity_2_plus_beat(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    ctx.template = "studio"
    long_text = " ".join([GOOD] * 12)  # 720 words per segment, 1440 total
    fake, _ = model([out(text=long_text, key_moment_labels={"b-02": "Not the right beat"})])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    with pytest.raises(StageError, match="key_moment_labels.*b-01"):
        script.run(ctx)
    fake, _ = model([out(text=long_text)])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)  # b-02 has intensity 1: no label needed


def test_shorts_prompt_names_the_single_beat_it_is_about(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    systems = []
    fake, calls = model([out()], systems)
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    request, _ = json.JSONDecoder().raw_decode(calls[0])
    assert request["short_beat"] == {"beat_id": "b-01", "type": "blunder", "ply": 1, "san": "e4", "pose": "facepalm"}
    assert [b["beat_id"] for b in request["facts"]["beats.json"]] == ["b-01"]
    assert "short_beat" in systems[0]


def test_long_form_prompt_has_no_short_beat(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    ctx.template = "studio"
    fake, calls = model([out(text=" ".join([GOOD] * 12), key_moment_labels={"b-01": "The slip"})])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    assert "short_beat" not in calls[0] and len(json.loads(calls[0])["facts"]["beats.json"]) == 2
