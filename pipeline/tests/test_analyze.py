import chess
import chess.engine
import pytest

from chesscode.engine_cache import EngineCache
from chesscode.stages.analyze import analyse_game


PGN = '''[Event "Test"]
[Result "1-0"]

1. e4 {[%clk 1:30:00]} e5 2. Qh5 1-0
'''


class Score:
    def __init__(self, cp):
        self.cp = cp

    def white(self):
        return self

    def score(self, mate_score=None):
        return self.cp

    def mate(self):
        return None


class FakeEngine:
    def __init__(self):
        self.calls = 0

    def analyse(self, board, limit, multipv):
        self.calls += 1
        return [
            {"score": Score(30), "pv": [chess.Move.from_uci("e2e4")]},
            {"score": Score(0), "pv": [chess.Move.from_uci("d2d4")]},
        ]


def test_cache_prevents_second_engine_call(tmp_path):
    engine = FakeEngine()
    make_engine = lambda: engine
    cache = EngineCache(tmp_path / "cache.sqlite")
    first = analyse_game(PGN, make_engine, cache)
    calls = engine.calls
    second = analyse_game(PGN, make_engine, cache)
    assert first == second
    assert engine.calls == calls


def test_clock_parsed_from_clk(tmp_path):
    rows = analyse_game(PGN, FakeEngine, EngineCache(tmp_path / "cache.sqlite"))
    assert rows[0]["clock_ms"] == 5400000


def test_no_clk_gives_none(tmp_path):
    rows = analyse_game(PGN.replace(" {[%clk 1:30:00]}", ""), FakeEngine, EngineCache(tmp_path / "cache.sqlite"))
    assert all(row["clock_ms"] is None for row in rows)


def test_final_ply_after_is_none(tmp_path):
    rows = analyse_game(PGN, FakeEngine, EngineCache(tmp_path / "cache.sqlite"))
    assert rows[-1]["after"] is None


@pytest.mark.engine
def test_real_engine_depth_20_multipv_2(tmp_path):
    import os
    from chesscode.stages import analyze
    path = os.environ.get("STOCKFISH_PATH")
    if not path:
        pytest.skip("STOCKFISH_PATH is not set")
    rows = analyze.analyse_game(PGN, lambda: chess.engine.SimpleEngine.popen_uci(path), EngineCache(tmp_path / "cache.sqlite"))
    assert rows and len(rows[0]["before"]) == 2


def _ctx(tmp_path, source_id="opera"):
    import shutil
    from pathlib import Path
    from chesscode.context import Context
    golden = Path(__file__).parent / "golden"
    spec = tmp_path / "spec"
    spec.mkdir()
    shutil.copyfile(golden / "pgn" / "opera.pgn", spec / "game.pgn")
    repo = tmp_path / "repo"
    (repo / "content" / "analysis").mkdir(parents=True)
    shutil.copyfile(golden / "analysis" / "opera.json", repo / "content" / "analysis" / f"{source_id}.json")
    return Context("cc-2026-0001-en", spec, repo, {"source_id": source_id}, "en", "studio")


def test_committed_analysis_is_used_without_an_engine(tmp_path, monkeypatch):
    import json
    from chesscode.stages import analyze
    monkeypatch.delenv("STOCKFISH_PATH", raising=False)
    ctx = _ctx(tmp_path)
    analyze.run(ctx)
    assert json.loads((ctx.spec_dir / "analysis.json").read_text(encoding="utf-8"))[0]["san"] == "e4"


def test_committed_analysis_for_another_game_is_refused(tmp_path):
    from pathlib import Path
    from chesscode.context import StageError
    from chesscode.stages import analyze
    ctx = _ctx(tmp_path)
    (ctx.spec_dir / "game.pgn").write_text((Path(__file__).parent / "golden" / "pgn" / "immortal.pgn").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(StageError, match="does not match"):
        analyze.run(ctx)
