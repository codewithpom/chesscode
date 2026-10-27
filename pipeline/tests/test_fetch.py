import json

import pytest

from chesscode.context import Context, StageError
from chesscode.stages import fetch, select


class Response:
    def __init__(self, status, text="[Event \"Test\"]\n\n1. e4 *\n"):
        self.status_code = status
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return next(self.responses)


def ctx(tmp_path, game):
    return Context("cc-2026-0001-en", tmp_path / "spec", tmp_path, game, "en", "studio")


def test_429_sleeps_60_then_succeeds(tmp_path, monkeypatch):
    session = Session([Response(429), Response(200)])
    sleeps = []
    monkeypatch.setattr(fetch, "session", session)
    monkeypatch.setattr(fetch, "sleep", lambda seconds: sleeps.append(seconds))
    game = {"source": "lichess", "source_id": "abcdefgh"}
    fetch.run(ctx(tmp_path, game))
    assert sleeps and sleeps[0] >= 60
    assert (tmp_path / "spec" / "game.pgn").is_file()
    assert len(session.calls) == 2


def test_cache_hit_no_request(tmp_path, monkeypatch):
    session = Session([])
    monkeypatch.setattr(fetch, "session", session)
    cache = tmp_path / "data" / "pgn" / "abcdefgh.pgn"
    cache.parent.mkdir(parents=True)
    cache.write_text("cached")
    fetch.run(ctx(tmp_path, {"source": "lichess", "source_id": "abcdefgh"}))
    assert session.calls == []
    assert (tmp_path / "spec" / "game.pgn").read_text() == "cached"


def test_local_pgn_copied(tmp_path):
    source = tmp_path / "source.pgn"
    source.write_text("local pgn")
    fetch.run(ctx(tmp_path, {"source": "local", "pgn_file": str(source), "source_id": "local-1"}))
    assert (tmp_path / "spec" / "game.pgn").read_text() == "local pgn"


def test_missing_source_raises_stage_error(tmp_path):
    with pytest.raises(StageError):
        fetch.run(ctx(tmp_path, {"source": "local", "pgn_file": "absent.pgn", "source_id": "absent"}))


def test_next_unrendered_respects_tier_and_order():
    games = [
        {"game_no": 1, "tier": "floor"},
        {"game_no": 2, "tier": "target"},
        {"game_no": 3, "tier": "floor"},
    ]
    assert select.next_unrendered(games, {"cc-2026-0001-en"}, "floor") == games[2]
