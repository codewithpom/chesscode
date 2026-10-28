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
GOOD = " ".join(["Pawn to e4 claims the centre"] * 10)  # 60 words


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
            return {"bad": []}
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


def long_out(km=GOOD, **extra):
    """A long-form script: 1400 words of play-by-play plus the key_moment segment for beat b-01 (ply 1)."""
    text = " ".join([GOOD] * 11)  # 660 words
    segments = [{"kind": "cold_open", "ply": None, "text": text}, {"kind": "ply", "ply": 1, "text": text}]
    if km is not None:
        segments.append({"kind": "key_moment", "ply": 1, "text": km})
    return out(segments=segments, **extra)


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
    fake, _ = model([long_out(key_moment_labels={"b-02": "Not the right beat"})])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    with pytest.raises(StageError, match="key_moment_labels.*b-01"):
        script.run(ctx)
    fake, _ = model([long_out()])
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
    fake, calls = model([long_out()])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    assert "short_beat" not in calls[0] and len(json.loads(calls[0])["facts"]["beats.json"]) == 2


def run_long(tmp_path, monkeypatch, outputs):
    ctx = setup_run(tmp_path, monkeypatch)
    ctx.template = "studio"
    fake, calls = model(outputs)
    monkeypatch.setattr(script.llm, "complete_json", fake)
    return ctx, calls


def test_long_form_request_gives_the_key_moment_word_range(tmp_path, monkeypatch):
    ctx, calls = run_long(tmp_path, monkeypatch, [long_out()])
    script.run(ctx)
    assert json.loads(calls[0])["key_moment_words"] == {"min": 45, "max": 90}


def test_missing_key_moment_segment_is_regenerated_once(tmp_path, monkeypatch):
    ctx, calls = run_long(tmp_path, monkeypatch, [long_out(km=None), long_out()])
    script.run(ctx)
    assert len(calls) == 2 and "key_moment segment" in calls[1]
    assert [s["kind"] for s in json.loads((ctx.spec_dir / "script.json").read_text())["segments"]].count("key_moment") == 1


@pytest.mark.parametrize("km,match", [
    (None, r"beat b-01 \(ply 1\) needs exactly one key_moment segment.*found 0"),
    ("short " * 10, "has 10 words, outside 45..90"),
    ("long " * 91, "has 91 words, outside 45..90"),
])
def test_long_form_without_a_valid_key_moment_stops(tmp_path, monkeypatch, km, match):
    ctx, _ = run_long(tmp_path, monkeypatch, [long_out(km=km)])
    with pytest.raises(StageError, match=match):
        script.run(ctx)


def test_duplicate_or_stray_key_moment_segments_are_rejected():
    beats = [{"beat_id": "b-01", "ply": 1, "intensity": 2}, {"beat_id": "b-02", "ply": 9, "intensity": 1}]
    seg = lambda ply: {"kind": "key_moment", "ply": ply, "text": GOOD}
    assert script.key_moment_problems([seg(1)], beats, 45, 90) == []
    assert "found 2" in script.key_moment_problems([seg(1), seg(1)], beats, 45, 90)[0]
    assert "matches no beat" in script.key_moment_problems([seg(1), seg(9)], beats, 45, 90)[0]


def test_prompt_no_longer_contradicts_itself_on_key_moment_ply():
    text = (ROOT / "pipeline/chesscode/prompts/script_system.md").read_text(encoding="utf-8")
    assert '"key_moment", "verdict" and "outro" (ply null)' not in text
    assert 'exactly one segment of kind "key_moment"' in text


def test_friday_teaser_short_is_about_a_different_beat(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    ctx.video_id = "cc-2026-6001-en"
    beats = [{"beat_id": "b-01", "type": "blunder", "ply": 1, "intensity": 2, "priority": 0, "pose": "facepalm"},
             {"beat_id": "b-02", "type": "mistake", "ply": 20, "intensity": 1, "priority": 9, "pose": "side_eye"}]
    (ctx.spec_dir / "beats.json").write_text(json.dumps(beats))
    rows = json.loads((ctx.spec_dir / "classified.json").read_text())
    (ctx.spec_dir / "classified.json").write_text(json.dumps(rows + [{**rows[0], "ply": 20, "san": "Nf3"}]))
    fake, calls = model([out(lines={"b-02": "Oops again."}, key_moment_labels={})])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    assert json.loads(calls[0])["short_beat"]["beat_id"] == "b-02"
    other = Context("cc-2026-5001-en", ctx.spec_dir, ctx.repo_root, {}, "en", "shorts")
    calls.clear(); script.run(other)
    assert json.loads(calls[0])["short_beat"]["beat_id"] == "b-01"  # the 5000-range Short keeps the top beat


def test_friday_teaser_without_a_second_beat_is_a_stage_error(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    ctx.video_id = "cc-2026-6001-en"  # fixture beats sit on the same ply
    fake, _ = model([out()])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    with pytest.raises(StageError, match=r"cc-2026-6001-en \[script\]: no second beat"):
        script.run(ctx)


def test_success_commits_the_script_and_a_rerun_replays_it_without_the_model(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    fake, calls = model([out()])
    monkeypatch.setattr(script.llm, "complete_json", fake)
    script.run(ctx)
    committed = ctx.repo_root / "content/scripts" / f"{ctx.video_id}.json"
    assert json.loads(committed.read_text(encoding="utf-8")) == json.loads((ctx.spec_dir / "script.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(script.llm, "complete_json", lambda *a: pytest.fail("replay must not call the model"))
    (ctx.spec_dir / "script.json").unlink()
    script.run(ctx)
    assert (ctx.spec_dir / "script.json").is_file()


def test_committed_script_with_an_unknown_move_is_refused(tmp_path, monkeypatch):
    ctx = setup_run(tmp_path, monkeypatch)
    committed = ctx.repo_root / "content/scripts" / f"{ctx.video_id}.json"
    committed.parent.mkdir(parents=True)
    committed.write_text(json.dumps(out(hook="Then Qh5 wins.")), encoding="utf-8")
    with pytest.raises(StageError, match="Qh5"):
        script.run(ctx)
