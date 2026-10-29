import io
import json
import os
from pathlib import Path

import chess
import chess.engine
import chess.pgn

from ..context import StageError
from ..engine_cache import EngineCache

INPUTS = ["game.pgn", "content/analysis"]
OUTPUTS = ["analysis.json"]


def _lines(engine, board: chess.Board, cache: EngineCache, depth: int, multipv: int) -> list[dict]:
    fen = board.fen()
    cached = cache.get(fen, depth, multipv)
    if cached is not None:
        return cached
    infos = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=multipv)
    if isinstance(infos, dict):
        infos = [infos]
    lines = []
    for info in infos:
        score = info["score"].white()
        mate = score.mate()
        lines.append({
            "uci": info["pv"][0].uci() if info.get("pv") else "",
            "cp": score.score() if mate is None else None,
            "mate": mate,
            "pv": [move.uci() for move in info.get("pv", [])],
        })
    cache.put(fen, depth, multipv, lines)
    return lines


def analyse_game(pgn: str, engine_factory, cache: EngineCache, depth: int = 20, multipv: int = 2) -> list[dict]:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("PGN contains no game")
    engine = None
    rows = []
    board = game.board()
    try:
        for node in game.mainline():
            before = _lines(engine := engine or engine_factory(), board, cache, depth, multipv)
            fen_before = board.fen()
            move = node.move
            san = board.san(move)
            board.push(move)
            after = None if not node.variations else _lines(engine := engine or engine_factory(), board, cache, depth, multipv)
            rows.append({
                "ply": board.ply(), "san": san, "uci": move.uci(),
                "fen_before": fen_before, "fen_after": board.fen(),
                "clock_ms": int(node.clock() * 1000) if node.clock() is not None else None,
                "before": before, "after": after,
            })
    finally:
        if engine is not None and hasattr(engine, "quit"):
            engine.quit()
    return rows


def _matches(rows: list[dict], pgn: str) -> bool:
    game = chess.pgn.read_game(io.StringIO(pgn))
    return [row.get("uci") for row in rows] == [move.uci() for move in game.mainline_moves()]


def run(ctx) -> None:
    pgn_path = ctx.spec_dir / "game.pgn"
    if not pgn_path.is_file():
        raise StageError(ctx.video_id, "analyze", "game.pgn is missing")
    # Committed analysis is the source of truth: engine builds, threads and hardware differ between
    # machines, and scripts written against one analysis must replay against the same one on Actions.
    committed = ctx.repo_root / "content" / "analysis" / f"{ctx.game.get('source_id')}.json"
    if committed.is_file():
        rows = json.loads(committed.read_text(encoding="utf-8"))
        if not _matches(rows, pgn_path.read_text(encoding="utf-8")):
            raise StageError(ctx.video_id, "analyze", f"{committed.name} does not match game.pgn move for move; delete it to re-analyse")
        (ctx.spec_dir / "analysis.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        return
    engine_path = os.environ.get("STOCKFISH_PATH")
    if not engine_path:
        raise StageError(ctx.video_id, "analyze", "STOCKFISH_PATH is not set")
    cache = EngineCache(ctx.repo_root / "data" / "engine_cache.sqlite")
    try:
        rows = analyse_game(
            pgn_path.read_text(encoding="utf-8"),
            lambda: _engine(engine_path),
            cache,
        )
    except Exception as exc:
        raise StageError(ctx.video_id, "analyze", str(exc)) from exc
    (ctx.spec_dir / "analysis.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    committed.parent.mkdir(parents=True, exist_ok=True)
    committed.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def _engine(path: str):
    engine = chess.engine.SimpleEngine.popen_uci(path)
    # More threads are fine now that the analysis is committed rather than recomputed per machine.
    engine.configure({"Threads": int(os.environ.get("STOCKFISH_THREADS", "1")), "Hash": int(os.environ.get("STOCKFISH_HASH_MB", "64"))})
    return engine
