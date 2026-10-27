"""opening_stats.py — Real opening win/draw/loss/popularity stats from the
free Lichess Opening Explorer API (no key required).

Every failure mode (network error, bad payload, too few games) returns None —
callers must treat None as "hide this stat," never fabricate numbers.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import List, Optional

from cache_utils import cache_key, get_cached

logger = logging.getLogger(__name__)

_EXPLORER_URL = "https://explorer.lichess.ovh/lichess"


@dataclass
class OpeningStats:
    opening_name: str
    white_win_pct: float
    draw_pct: float
    black_win_pct: float
    total_games: int


def get_opening_stats(opening_name: str, moves_san: str = "",
                      cache_dir: str = "output/.cache/opening_stats",
                      min_games: int = 5, timeout: float = 6.0
                      ) -> Optional[OpeningStats]:
    """Fetch real win/draw/loss % + popularity for the opening played in this
    game, keyed off its own opening moves. Returns None on any failure or if
    the sample size is too small to be meaningful."""
    play_moves = _san_to_uci_play_list(moves_san)
    if not play_moves:
        return None

    key = cache_key("opening_explorer_v1", ",".join(play_moves))
    cached_path = get_cached(cache_dir, key, ".json")
    if cached_path:
        try:
            with open(cached_path, encoding="utf-8") as f:
                data = json.load(f)
            return _parse_explorer_payload(opening_name, data, min_games)
        except Exception as e:
            logger.warning(f"opening_stats: cached payload unreadable, refetching: {e}")

    data = _query_lichess_explorer(play_moves, timeout)
    if data is None:
        return None

    try:
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, f"{key}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError as e:
        logger.warning(f"opening_stats: failed to write cache: {e}")

    return _parse_explorer_payload(opening_name, data, min_games)


def _parse_explorer_payload(opening_name: str, data: dict, min_games: int
                            ) -> Optional[OpeningStats]:
    try:
        white = int(data.get("white", 0))
        draws = int(data.get("draws", 0))
        black = int(data.get("black", 0))
    except (TypeError, ValueError):
        return None

    total = white + draws + black
    if total < min_games:
        return None

    return OpeningStats(
        opening_name=opening_name,
        white_win_pct=round(100.0 * white / total, 1),
        draw_pct=round(100.0 * draws / total, 1),
        black_win_pct=round(100.0 * black / total, 1),
        total_games=total,
    )


def _query_lichess_explorer(play_uci_moves: List[str], timeout: float) -> Optional[dict]:
    try:
        import requests
        resp = requests.get(_EXPLORER_URL, params={
            "variant": "standard",
            "play": ",".join(play_uci_moves),
            "speeds": "blitz,rapid,classical",
            "ratings": "1600,1800,2000,2200,2500",
        }, headers={"User-Agent": "ChessCode/1.0", "Accept": "application/json"},
           timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"opening_stats: Lichess Explorer request failed: {e}")
        return None


def _san_to_uci_play_list(moves_san: str, max_plies: int = 8) -> List[str]:
    """Convert a whitespace-separated SAN move string (move numbers optional,
    e.g. '1. e4 c5 2. Nf3 d6') into a list of UCI move strings by replaying
    them on a fresh board. Stops early/returns what it has if a move fails
    to parse (never raises)."""
    if not moves_san or not moves_san.strip():
        return []
    try:
        import chess
    except ImportError:
        return []

    board = chess.Board()
    uci_moves = []
    tokens = moves_san.replace(".", ". ").split()
    for tok in tokens:
        if len(uci_moves) >= max_plies:
            break
        if not tok or tok[0].isdigit():
            continue
        try:
            move = board.parse_san(tok)
        except (ValueError, chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError):
            break
        board.push(move)
        uci_moves.append(move.uci())

    return uci_moves
