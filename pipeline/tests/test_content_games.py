"""content/games.yaml is the backlog: enough games, sourced PGNs, rotating series, and a full floor calendar."""
from collections import Counter
from pathlib import Path

import chess.pgn
import yaml

from chesscode import calendar

ROOT = Path(__file__).resolve().parents[2]
GAMES = yaml.safe_load((ROOT / "content" / "games.yaml").read_text(encoding="utf-8"))


def test_backlog_size_and_series_balance():
    assert len(GAMES) >= 70
    assert [g["game_no"] for g in GAMES] == list(range(1, len(GAMES) + 1))
    assert min(Counter(g["series"] for g in GAMES).values()) >= 17
    assert Counter(g["tier"] for g in GAMES)["floor"] == 13 and Counter(g["tier"] for g in GAMES)["target"] == 13


def test_every_game_has_its_pgn_and_no_game_repeats():
    moves = []
    for g in GAMES:
        path = ROOT / g["pgn_file"]
        assert path.is_file(), g["pgn_file"]
        with path.open(encoding="utf-8") as f:
            moves.append(" ".join(m.uci() for m in chess.pgn.read_game(f).mainline_moves()))
    assert len(set(moves)) == len(moves)


def test_no_series_runs_three_weeks_in_a_row_in_either_slot():
    for tier in ("floor", "target"):
        series = [g["series"] for g in GAMES if g["tier"] == tier]
        assert all(not (a == b == c) for a, b, c in zip(series, series[1:], series[2:])), tier


def test_calendar_places_every_floor_and_target_video():
    _, unassigned = calendar.schedule(GAMES, root=ROOT)
    placed_tiers = {g["game_no"] for g in GAMES if g["tier"] in ("floor", "target")}
    bad = {vid: why for vid, why in unassigned.items() if int(vid.split("-")[2]) % 1000 in placed_tiers}
    assert not bad
