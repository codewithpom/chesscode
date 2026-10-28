import csv
import io
import json
from pathlib import Path

import chess
import chess.pgn

from ..config import load
from ..context import StageError
from ..winprob import win_pct

INPUTS = ["analysis.json", "config/classify.yaml", "content/openings"]
OUTPUTS = ["classified.json"]
_VALUES = {
    chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
    chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0,
}


def load_openings(directory: Path) -> set[str]:
    positions = set()
    for path in sorted(Path(directory).glob("*.tsv")):
        with path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            if not {"eco", "name", "pgn"}.issubset(reader.fieldnames or []):
                raise ValueError(f"{path} must have eco, name, and pgn columns")
            for entry in reader:
                game = chess.pgn.read_game(io.StringIO(entry["pgn"]))
                if game is None:
                    raise ValueError(f"{path} contains an invalid PGN")
                board = game.board()
                for node in game.mainline():
                    board.push(node.move)
                    positions.add(board.epd())
    return positions


def _material(board: chess.Board, color: chess.Color) -> int:
    return sum(_VALUES[piece.piece_type] for piece in board.piece_map().values() if piece.color == color)


def _material_given(row: dict) -> float:
    if not row.get("after"):
        return 0
    before = chess.Board(row["fen_before"])
    after = chess.Board(row["fen_after"])
    mover = before.turn

    def balance(board):
        white = _material(board, chess.WHITE)
        black = _material(board, chess.BLACK)
        return white - black if mover == chess.WHITE else black - white

    initial = balance(before)
    try:
        # The played move is already reflected in fen_after. Only inspect the
        # opponent's reply and the mover's following move for a sacrifice.
        for uci in row["after"][0].get("pv", [])[:2]:
            after.push_uci(uci)
    except (ValueError, chess.IllegalMoveError):
        return 0
    return initial - balance(after)


def _score(line: dict) -> tuple[int | None, int | None]:
    return line.get("cp"), line.get("mate")


def _pawns(line: dict, color: chess.Color) -> float:
    cp, mate = _score(line)
    if mate is not None:
        white_wins = mate > 0
        return float("inf") if white_wins == color else float("-inf")
    if cp is None:
        raise ValueError("analysis line has neither cp nor mate")
    return (cp if color == chess.WHITE else -cp) / 100


def classify_ply(row: dict, in_book: bool, cfg: dict) -> str:
    if in_book:
        return "book"
    before = row.get("before") or []
    if not before:
        raise ValueError("analysis row is missing before lines")
    after = row.get("after")
    played = after[0] if after else before[0]
    best = before[0]
    mover = chess.Board(row["fen_before"]).turn
    best_cp, best_mate = _score(best)
    played_cp, played_mate = _score(played)
    best_pct = win_pct(best_cp, best_mate)
    played_pct = win_pct(played_cp, played_mate)
    loss = best_pct - played_pct if mover == chess.WHITE else played_pct - best_pct

    brilliant = cfg["brilliant"]
    decided_guard = _pawns(best, mover) < cfg.get("brilliant_decided_pawns", 5.0) or row.get("uci") == best.get("uci")
    if loss <= brilliant["max_loss"] and _material_given(row) >= brilliant["min_material_given"] and decided_guard:
        return "brilliant"
    missed = cfg["missed_win"]
    if best_mate is None and played_mate is None and _pawns(best, mover) >= missed["best_min_pawns"] and _pawns(played, mover) <= missed["played_max_pawns"]:
        return "missed_win"
    if row.get("uci") == best.get("uci"):
        return "best"
    if loss < cfg["excellent_max_loss"]:
        return "excellent"
    if loss < cfg["good_max_loss"]:
        return "good"
    if loss < cfg["inaccuracy_max_loss"]:
        return "inaccuracy"
    if loss < cfg["mistake_max_loss"]:
        return "mistake"
    return "blunder"


def run(ctx) -> None:
    openings_dir = ctx.repo_root / "content" / "openings"
    openings = load_openings(openings_dir)
    if not openings:
        raise StageError(ctx.video_id, "classify", f"no opening TSV positions found in {openings_dir}")
    analysis_path = ctx.spec_dir / "analysis.json"
    if not analysis_path.is_file():
        raise StageError(ctx.video_id, "classify", "analysis.json is missing")
    try:
        rows = json.loads(analysis_path.read_text(encoding="utf-8"))
        cfg = load("classify", root=ctx.repo_root)
        classified = []
        for row in rows:
            epd = chess.Board(row["fen_after"]).epd()
            best = row["before"][0]
            score = (row.get("after") or row["before"])[0]
            classified.append({
                **row,
                "class": classify_ply(row, epd in openings, cfg),
                "eval": {"cp": score.get("cp"), "mate": score.get("mate")},
                "best_uci": best["uci"],
            })
    except Exception as exc:
        raise StageError(ctx.video_id, "classify", str(exc)) from exc
    (ctx.spec_dir / "classified.json").write_text(json.dumps(classified, indent=2) + "\n", encoding="utf-8")
