"""emit.assemble: no silent defaults, poses/arrows/check highlights/sfx from data, music copied into the folder."""
import copy
import json
from pathlib import Path

import chess
import pytest
import yaml

from chesscode.context import Context, StageError
from chesscode.stages import emit

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((ROOT / "spec/fixtures/cc-2026-0001-en/video_spec.json").read_text(encoding="utf-8"))


def make_dir(tmp_path, pgn=None, beats=None, game_extra=None, plies=None):
    spec = tmp_path / "spec"
    spec.mkdir()
    timeline_beats = beats or [{"beat_id": b["beat_id"], "type": b["type"], "ply": b["ply"], "at_ms": b["at_ms"], "intensity": b["intensity"], "pose": b["mascot"]["pose"]} for b in FIXTURE["beats"]]
    files = {
        "game.json": {"source": "local", "source_id": "opera-game-1858", "series": "legendary_games", "white_country": "US", "black_country": None, **(game_extra or {})},
        "classified.json": plies or [{k: p[k] for k in ("ply", "san", "uci", "fen_after", "eval", "best_uci", "class", "clock_ms")} for p in FIXTURE["plies"]],
        "beats.json": timeline_beats,
        "script.json": {"mascot_lines": {b["beat_id"]: b["mascot"]["line"] for b in FIXTURE["beats"]}},
        "timeline.json": {"narration": FIXTURE["narration"], "beats": timeline_beats, "chapters": FIXTURE["chapters"], "duration_ms": 60000, "plies_show_at": {str(p["ply"]): p["show_at_ms"] for p in FIXTURE["plies"]}},
        "metadata.json": FIXTURE["youtube"],
    }
    for name, value in files.items():
        (spec / name).write_text(json.dumps(value), encoding="utf-8")
    (spec / "game.pgn").write_text(pgn or FIXTURE["game"]["pgn"], encoding="utf-8")
    return Context("cc-2026-0001-en", spec, ROOT, {}, "en", "studio")


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
    (ctx.spec_dir / "script.json").write_text(json.dumps({"mascot_lines": {}}))
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
