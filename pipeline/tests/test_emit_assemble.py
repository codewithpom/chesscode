"""emit.assemble: no silent defaults, poses/arrows/check highlights/sfx from data, music copied into the folder."""
import copy
import json
import math
from pathlib import Path

import chess
import pytest
import yaml

from chesscode.context import Context, StageError
from chesscode.stages import emit

ROOT = Path(__file__).resolve().parents[2]
PRIORITY = yaml.safe_load((ROOT / "config/beats.yaml").read_text(encoding="utf-8"))["priority"]
FIXTURE = json.loads((ROOT / "spec/fixtures/cc-2026-0001-en/video_spec.json").read_text(encoding="utf-8"))


def with_before(rows):
    """Slim fixture rows plus the engine's pre-move line, as classify leaves them."""
    previous = {"cp": 0, "mate": None}
    out = []
    for p in rows:
        out.append({**p, "before": [{"uci": p["best_uci"], **previous, "pv": [p["best_uci"], p["uci"]]}]})
        previous = p["eval"]
    return out


def make_dir(tmp_path, pgn=None, beats=None, game_extra=None, plies=None, script_extra=None, template="studio"):
    spec = tmp_path / "spec"
    spec.mkdir()
    timeline_beats = beats or [{"beat_id": b["beat_id"], "type": b["type"], "ply": b["ply"], "at_ms": b["at_ms"], "intensity": b["intensity"], "pose": b["mascot"]["pose"]} for b in FIXTURE["beats"]]
    timeline_beats = [{**b, "priority": PRIORITY.index(b["type"])} for b in timeline_beats]
    files = {
        "game.json": {"source": "local", "source_id": "opera-game-1858", "series": "legendary_games", "white_country": "US", "black_country": None, **(game_extra or {})},
        "classified.json": plies or with_before([{k: p[k] for k in ("ply", "san", "uci", "fen_after", "eval", "best_uci", "class", "clock_ms")} for p in FIXTURE["plies"]]),
        "beats.json": timeline_beats,
        "script.json": {"mascot_lines": {b["beat_id"]: b["mascot"]["line"] for b in FIXTURE["beats"]},
                        "player_facts": {"white": "White fact.", "black": "Black fact."}, "cold_open_hook": "Mate in a flash",
                        "thumbnail_text": "Queen sac mate", "key_moment_labels": {"b-01": "Early exit", "b-02": "The mating net"}, **(script_extra or {})},
        "timeline.json": {"narration": FIXTURE["narration"], "beats": timeline_beats, "chapters": FIXTURE["chapters"], "duration_ms": 60000, "plies_show_at": {str(p["ply"]): p["show_at_ms"] for p in FIXTURE["plies"]}},
        "metadata.json": FIXTURE["youtube"],
    }
    for name, value in files.items():
        (spec / name).write_text(json.dumps(value), encoding="utf-8")
    (spec / "game.pgn").write_text(pgn or FIXTURE["game"]["pgn"], encoding="utf-8")
    return Context("cc-2026-0001-en", spec, ROOT, {}, "en", template)


def test_assemble_validates_and_keeps_beat_pose_fx_sfx(tmp_path):
    beats = [{"beat_id": "b-01", "type": "blunder", "ply": 7, "at_ms": 11300, "intensity": 3, "pose": "faint"},
             {"beat_id": "b-02", "type": "checkmate", "ply": 33, "at_ms": 35000, "intensity": 3, "pose": "mic_drop"}]
    ctx = make_dir(tmp_path, beats=beats)
    spec = emit.assemble(ctx)
    emit.validate(spec)
    assert spec["beats"][0]["mascot"]["pose"] == "faint"      # not the hard-coded facepalm
    assert spec["beats"][0]["sfx"] == "oof_01" and spec["beats"][1]["sfx"] == "sting_01"
    assert spec["game"]["opening"] == "Philidor Defense" and spec["game"]["eco"] == "C41"


@pytest.mark.parametrize("header", ["Event", "Date", "White", "Black", "ECO"])
def test_missing_pgn_header_stops_with_reason(tmp_path, header):
    pgn = "\n".join(line for line in FIXTURE["game"]["pgn"].splitlines() if not line.startswith(f"[{header} "))
    ctx = make_dir(tmp_path, pgn=pgn)
    with pytest.raises(StageError, match=header):
        emit.run(ctx)
    assert not (ctx.spec_dir / "video_spec.json").exists()


def test_unfinished_result_is_not_defaulted(tmp_path):
    pgn = FIXTURE["game"]["pgn"].replace('[Result "1-0"]', '[Result "*"]').replace("Rd8# 1-0", "Rd8# *")
    with pytest.raises(StageError, match="Result"):
        emit.run(make_dir(tmp_path, pgn=pgn))


def test_missing_mascot_line_and_show_time_stop(tmp_path):
    ctx = make_dir(tmp_path)
    data = json.loads((ctx.spec_dir / "script.json").read_text())
    (ctx.spec_dir / "script.json").write_text(json.dumps({**data, "mascot_lines": {}}))
    with pytest.raises(StageError, match="mascot line"):
        emit.run(ctx)
    (tmp_path / "again").mkdir()
    ctx = make_dir(tmp_path / "again")
    data = json.loads((ctx.spec_dir / "timeline.json").read_text())
    del data["plies_show_at"]["3"]
    (ctx.spec_dir / "timeline.json").write_text(json.dumps(data))
    with pytest.raises(StageError, match="3"):
        emit.run(ctx)


def test_unknown_source_game_fields_stop(tmp_path):
    ctx = make_dir(tmp_path)
    (ctx.spec_dir / "game.json").write_text(json.dumps({"source": "local", "series": "legendary_games"}))
    with pytest.raises(StageError, match="source_id"):
        emit.run(ctx)


def test_blunder_gets_best_move_arrow_and_missed_win_gets_missed_arrow():
    row = {"class": "blunder", "uci": "e2e4", "best_uci": "d2d4"}
    assert emit.arrows(row) == [{"from": "d2", "to": "d4", "color": "best"}]
    assert emit.arrows({**row, "class": "missed_win"}) == [{"from": "d2", "to": "d4", "color": "missed"}]
    assert emit.arrows({**row, "class": "good"}) == []
    assert emit.arrows({**row, "class": "blunder", "best_uci": "e2e4"}) == []


def test_check_highlight_on_the_king_in_check():
    fen = "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"  # white king in check from the queen
    marks = emit.highlights({"uci": "d8h4", "fen_after": fen})
    assert {"square": "e1", "kind": "check"} in marks
    assert {"square": "d8", "kind": "last_move"} in marks and {"square": "h4", "kind": "last_move"} in marks
    assert all(m["kind"] != "check" for m in emit.highlights({"uci": "e2e4", "fen_after": chess.STARTING_FEN}))


def test_music_is_copied_into_the_spec_folder_and_placeholder_is_marked(tmp_path):
    ctx = make_dir(tmp_path)
    spec = emit.assemble(ctx)
    track = ctx.spec_dir / spec["music"]["track"]
    assert track.is_file() and track.stat().st_size > 0
    assert (ctx.spec_dir / (spec["music"]["track"] + ".placeholder")).is_file()  # QA flags this


def test_licensed_track_is_copied_without_a_placeholder_marker(tmp_path):
    repo = tmp_path / "repo"
    (repo / "config").mkdir(parents=True)
    (repo / "content/music").mkdir(parents=True)
    (repo / "content/music/real.mp3").write_bytes(b"licensed audio")
    (repo / "config/music.yaml").write_text(yaml.safe_dump({"track": "real", "tracks": {"real": {"file": "content/music/real.mp3", "placeholder": False, "volume": 0.1, "duck_under_voice": 0.05, "credit": "Real Artist (CC0)"}}}))
    ctx = make_dir(tmp_path)
    ctx.repo_root = repo
    music = emit.prepare_music(ctx, 60000)
    assert music == {"track": "music/real.mp3", "volume": 0.1, "duck_under_voice": 0.05}
    assert (ctx.spec_dir / "music/real.mp3").read_bytes() == b"licensed audio"
    assert not (ctx.spec_dir / "music/real.mp3.placeholder").exists()
    (repo / "content/music/real.mp3").unlink()
    with pytest.raises(ValueError, match="real.mp3"):
        emit.prepare_music(ctx, 60000)


@pytest.mark.parametrize("value", ["2026-11-16", "2026-11-16T12:30:00+00:00", "2026-13-45T12:30:00Z", "not a date", "2026-02-30T12:30:00Z", ""])
def test_publish_at_must_be_iso_utc_z(value):
    spec = copy.deepcopy(FIXTURE)
    spec["youtube"]["publish_at"] = value
    with pytest.raises(StageError, match="publish_at"):
        emit.validate(spec)


def test_same_pose_twice_in_a_row_is_rejected():
    spec = copy.deepcopy(FIXTURE)
    spec["beats"][1]["mascot"]["pose"] = spec["beats"][0]["mascot"]["pose"]
    with pytest.raises(StageError, match="pose"):
        emit.validate(spec)


def test_chapters_live_at_top_level_only(tmp_path):
    ctx = make_dir(tmp_path)
    (ctx.spec_dir / "metadata.json").write_text(json.dumps({**FIXTURE["youtube"], "chapters": FIXTURE["chapters"]}))
    spec = emit.assemble(ctx)
    assert "chapters" not in spec["youtube"] and spec["chapters"] == FIXTURE["chapters"]


def test_contract_1_1_0_fields_come_from_the_stages_that_own_them(tmp_path):
    ctx = make_dir(tmp_path)
    spec = emit.assemble(ctx)
    emit.validate(spec)
    assert spec["spec_version"] == "1.1.0"
    assert spec["game"]["white"]["fact"] == "White fact." and spec["game"]["black"]["fact"] == "Black fact."
    # checkmate outranks opening_exit; the cold open replays the two plies before it
    assert spec["cold_open"] == {"ply_from": 31, "ply_to": 33, "hook": "Mate in a flash"}
    assert spec["thumbnail"] == {"text": "Queen sac mate", "ply": 33, "crop_origin": emit.crop_origin("d1d8"), "pose": "mic_drop"}
    assert 1 <= spec["verdict"]["turning_point_ply"] <= 33
    assert all(0 <= v <= 100 for v in spec["verdict"]["accuracy"].values())


def test_cold_open_starts_at_ply_one_for_an_early_beat(tmp_path):
    beats = [{"beat_id": "b-01", "type": "blunder", "ply": 2, "at_ms": 6000, "intensity": 2, "pose": "facepalm"}]
    spec = emit.assemble(make_dir(tmp_path, beats=beats, script_extra={"key_moment_labels": {"b-01": "Early slip"}}))
    assert (spec["cold_open"]["ply_from"], spec["cold_open"]["ply_to"]) == (1, 2)


def test_key_moments_one_per_intensity_2_plus_beat_with_timeline_timing(tmp_path):
    ctx = make_dir(tmp_path)
    spec = emit.assemble(ctx)
    narration = {n["segment_id"]: n for n in FIXTURE["narration"]}
    # b-01 is intensity 1 (no key moment); b-02's ply segment seg-007 covers ply 33
    assert [k["beat_id"] for k in spec["key_moments"]] == ["b-02"]
    k = spec["key_moments"][0]
    assert (k["ply"], k["start_ms"], k["duration_ms"], k["label"]) == (33, narration["seg-007"]["start_ms"], narration["seg-007"]["duration_ms"], "The mating net")
    assert k["line"] == ["d1d8", "d1d8"] and len(k["line"]) <= 8


def test_key_moment_narration_segment_wins_over_the_ply_segment(tmp_path):
    ctx = make_dir(tmp_path)
    data = json.loads((ctx.spec_dir / "timeline.json").read_text())
    data["narration"][0].update(kind="key_moment", ply=33)  # seg-000, 0..5000
    (ctx.spec_dir / "timeline.json").write_text(json.dumps(data))
    k = emit.assemble(ctx)["key_moments"][0]
    assert (k["start_ms"], k["duration_ms"]) == (0, 5000)


def test_shorts_have_no_key_moments(tmp_path):
    spec = emit.assemble(make_dir(tmp_path, template="shorts"))
    assert spec["key_moments"] == []


def test_key_moment_pv_is_cut_to_eight_moves(tmp_path):
    rows = with_before([{k: p[k] for k in ("ply", "san", "uci", "fen_after", "eval", "best_uci", "class", "clock_ms")} for p in FIXTURE["plies"]])
    rows[32]["before"][0]["pv"] = [f"a{i}a{i + 1}" for i in range(1, 8)] + ["h1h2", "h2h3"]
    assert len(emit.assemble(make_dir(tmp_path, plies=rows))["key_moments"][0]["line"]) == 8


@pytest.mark.parametrize("name,edit", [
    ("black", lambda s: s["player_facts"].pop("black")),
    ("cold_open_hook", lambda s: s.pop("cold_open_hook")),
    ("thumbnail_text", lambda s: s.pop("thumbnail_text")),
    ("b-02", lambda s: s["key_moment_labels"].pop("b-02")),
])
def test_missing_script_value_stops_emit(tmp_path, name, edit):
    ctx = make_dir(tmp_path)
    data = json.loads((ctx.spec_dir / "script.json").read_text())
    edit(data)
    (ctx.spec_dir / "script.json").write_text(json.dumps(data))
    with pytest.raises(StageError, match=name):
        emit.run(ctx)
    assert not (ctx.spec_dir / "video_spec.json").exists()


def test_crop_origin_contains_both_squares_and_stays_on_the_board():
    squares = [f + r for f in "abcdefgh" for r in "12345678"]
    for a in squares:
        for b in squares:
            origin = emit.crop_origin(a + b)
            f0, r0 = ord(origin[0]) - 97, int(origin[1]) - 1
            assert 0 <= f0 <= 4 and 0 <= r0 <= 4
            fits = abs(ord(a[0]) - ord(b[0])) <= 3 and abs(int(a[1]) - int(b[1])) <= 3
            for sq in (a, b) if fits else (b,):  # wider moves keep the destination
                assert f0 <= ord(sq[0]) - 97 <= f0 + 3 and r0 <= int(sq[1]) - 1 <= r0 + 3, (a, b, origin)
    assert emit.crop_origin("e2e4") == "d2"
    assert emit.crop_origin("h8g8") == "e5"


def row(ply, before, after):
    cp = lambda v: {"cp": v, "mate": None}
    return {"ply": ply, "before": [{"uci": "a2a3", "pv": ["a2a3"], **cp(before)}], "eval": cp(after)}


def test_verdict_turning_point_is_the_largest_swing_against_the_loser():
    # 1-0: black loses; the biggest white gain is ply 2
    rows = [row(1, 0, 40), row(2, 40, 400), row(3, 400, 300)]
    assert emit.verdict(rows, "1-0")["turning_point_ply"] == 2
    # 0-1: white loses; the biggest black gain is ply 2
    rows = [row(1, 0, -40), row(2, -40, -400), row(3, -400, 100)]
    assert emit.verdict(rows, "0-1")["turning_point_ply"] == 2


def test_verdict_draw_uses_largest_absolute_swing():
    rows = [row(1, 0, 20), row(2, 20, -300), row(3, -300, 0)]
    assert emit.verdict(rows, "1/2-1/2")["turning_point_ply"] == 2


def test_verdict_accuracy_is_the_lichess_formula_per_side():
    from chesscode.winprob import win_pct
    rows = [row(1, 0, -100), row(2, -100, -100), row(3, -100, 0)]  # white loses ~9% on ply 1 and gains on ply 3; black loses nothing
    loss = win_pct(0, None) - win_pct(-100, None)
    acc = lambda l: max(0, min(100, 103.1668 * math.exp(-0.04354 * l) - 3.1669))
    out = emit.verdict(rows, "1-0")["accuracy"]
    assert out["white"] == pytest.approx((acc(loss) + acc(-loss)) / 2, abs=0.01)
    assert out["black"] == pytest.approx(100.0, abs=0.01)


@pytest.mark.parametrize("edit,match", [
    (lambda s: s["cold_open"].update(ply_from=20, ply_to=10), "cold_open"),
    (lambda s: s["cold_open"].update(ply_to=34), "cold_open"),
    (lambda s: s["key_moments"].append({"beat_id": "b-99", "ply": 33, "start_ms": 0, "duration_ms": 10, "label": "x", "line": ["e2e4"]}), "beat_id"),
    (lambda s: s["key_moments"].append({"beat_id": "b-02", "ply": 99, "start_ms": 0, "duration_ms": 10, "label": "x", "line": ["e2e4"]}), "key_moments"),
    (lambda s: s["verdict"].update(turning_point_ply=34), "turning_point_ply"),
    (lambda s: s["thumbnail"].update(ply=34), "thumbnail"),
    (lambda s: (s["youtube"].update(title="Queen sac mate"), s["thumbnail"].update(text="QUEEN SAC mate")), "thumbnail.text"),
])
def test_validate_mirrors_the_zod_cross_field_checks(edit, match):
    spec = copy.deepcopy(FIXTURE)
    edit(spec)
    with pytest.raises(StageError, match=match):
        emit.validate(spec)
