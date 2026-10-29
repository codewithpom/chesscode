"""Validate content PGN files: python scripts/check_pgns.py [files...] (default content/pgn/*.pgn)."""
import io
import sys
from pathlib import Path

import chess
import chess.pgn

REQUIRED = ("White", "Black", "Event", "Date", "Result")
MIN_FULL_MOVES = 10


def check_pgn(path: Path) -> list[str]:
    """Return problems found in a one-game PGN file; empty list means OK."""
    text = Path(path).read_text(encoding="utf-8")
    stream = io.StringIO(text)
    game = chess.pgn.read_game(stream)
    if game is None:
        return ["no game found"]
    problems = []
    if chess.pgn.read_game(stream) is not None:
        problems.append("more than one game in file")
    problems += [f"parse/illegal move: {e}" for e in game.errors]
    for h in REQUIRED:
        if game.headers.get(h, "").strip() in ("", "?", "????.??.??"):  # python-chess fills "?" defaults
            problems.append(f"missing header {h}")
    board = game.end().board()
    plies = len(list(game.mainline_moves()))
    if (plies + 1) // 2 < MIN_FULL_MOVES:
        problems.append(f"game too short ({(plies + 1) // 2} moves)")
    result = game.headers.get("Result", "")
    if result not in ("1-0", "0-1", "1/2-1/2", "*"):
        problems.append(f"bad Result {result!r}")
    if board.is_checkmate():
        want = "0-1" if board.turn == chess.WHITE else "1-0"
        if result != want:
            problems.append(f"final position is mate but Result is {result}, expected {want}")
    return problems


if __name__ == "__main__":
    files = [Path(a) for a in sys.argv[1:]] or sorted(Path("content/pgn").glob("*.pgn"))
    bad = 0
    for f in files:
        probs = check_pgn(f)
        bad += bool(probs)
        print(f"{'FAIL' if probs else 'ok  '} {f.name} {'; '.join(probs)}")
    sys.exit(1 if bad else 0)
