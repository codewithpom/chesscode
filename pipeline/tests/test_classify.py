import chess
import json
import pytest
from pathlib import Path
import shutil
import yaml

from chesscode.stages import classify
from chesscode.winprob import win_pct

CFG = {
    "excellent_max_loss": 2, "good_max_loss": 5, "inaccuracy_max_loss": 10, "mistake_max_loss": 15,
    "brilliant": {"max_loss": 3, "min_material_given": 2},
    "missed_win": {"best_min_pawns": 3.0, "played_max_pawns": 1.0},
}


def line(cp, uci="e2e4", mate=None, pv=None):
    return {"uci": uci, "cp": None if mate is not None else cp, "mate": mate, "pv": pv or ([uci] if uci else [])}


def row(before_cp=0, after_cp=0, played="e2e4", best="d2d4", before_mate=None, after_mate=None):
    return {
        "ply": 1, "uci": played, "fen_before": chess.STARTING_FEN,
        "fen_after": _after_e4(),
        "before": [line(before_cp, best, before_mate)],
        "after": [line(after_cp, "e7e5", after_mate)],
    }


def _after_e4():
    board = chess.Board()
    board.push_san("e4")
    return board.fen()


def test_win_pct_symmetry():
    assert win_pct(325, None) + win_pct(-325, None) == pytest.approx(100)


def test_win_pct_mate():
    assert win_pct(None, 3) == 100
    assert win_pct(None, -3) == 0


def test_mate_flip_loss_is_100():
    assert classify.classify_ply(row(before_mate=3, after_mate=-1), False, CFG) == "blunder"


def test_bucket_edges(monkeypatch):
    cfg = CFG
    pct = {0: 50, 1: 45.1, 2: 45, 3: 35.1, 4: 35}
    monkeypatch.setattr(classify, "win_pct", lambda cp, mate: pct[cp])
    assert classify.classify_ply(row(0, 1), False, cfg) == "good"
    assert classify.classify_ply(row(0, 2), False, cfg) == "inaccuracy"
    assert classify.classify_ply(row(0, 3), False, cfg) == "mistake"
    assert classify.classify_ply(row(0, 4), False, cfg) == "blunder"


def test_brilliant_requires_material_sacrifice():
    board = chess.Board("r3k3/8/8/8/8/8/8/Q3K3 w - - 0 1")
    move = chess.Move.from_uci("e1f1")
    before_fen = board.fen()
    board.push(move)
    sacrifice = {
        "uci": move.uci(), "fen_before": before_fen, "fen_after": board.fen(),
        "before": [line(0, move.uci())], "after": [line(0, "a8a1", pv=["a8a1"])],
    }
    assert classify.classify_ply(sacrifice, False, CFG) == "brilliant"
    no_sacrifice = {**sacrifice, "after": [line(0, "a8b8", pv=["a8b8"])]}
    assert classify.classify_ply(no_sacrifice, False, CFG) != "brilliant"


def test_missed_win():
    assert classify.classify_ply(row(350, 80), False, CFG) == "missed_win"


def test_book_from_openings():
    openings = classify.load_openings(Path(__file__).parent / "fixtures" / "openings")
    board = chess.Board()
    board.push_san("e4")
    move = chess.Move.from_uci("e2e4")
    entry = row()
    entry.update(uci=move.uci(), fen_after=board.fen())
    assert classify.classify_ply(entry, board.epd() in openings, {}) == "book"


def test_run_writes_classified_rows(tmp_path):
    from chesscode.context import Context

    repo = tmp_path / "repo"
    spec_dir = tmp_path / "spec"
    openings = repo / "content" / "openings"
    openings.mkdir(parents=True)
    shutil.copy(Path(__file__).parent / "fixtures" / "openings" / "sample.tsv", openings / "sample.tsv")
    config_dir = repo / "config"
    config_dir.mkdir()
    (config_dir / "classify.yaml").write_text(yaml.safe_dump(CFG))
    spec_dir.mkdir()
    entry = row(350, 80)
    (spec_dir / "analysis.json").write_text(json.dumps([entry]))
    classify.run(Context("cc-2026-0001-en", spec_dir, repo, {}, "en", "studio"))
    result = json.loads((spec_dir / "classified.json").read_text())[0]
    assert result["class"] == "book"
    assert result["eval"] == {"cp": 80, "mate": None}
    assert result["best_uci"] == "d2d4"
