"""tests/test_lichess_api.py — Lichess GET proxy: allowlist + request shape."""

import pytest

import lichess_api


class _FakeResp:
    def __init__(self, status=200, json_data=None, text="", ctype="application/json"):
        self.status_code = status
        self._json = json_data
        self.text = text
        self.headers = {"Content-Type": ctype}

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


def test_disallowed_host_raises():
    with pytest.raises(lichess_api.LichessError):
        lichess_api.fetch("evil.com", "/x")


def test_allowed_host_builds_url_and_parses_json(monkeypatch):
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return _FakeResp(json_data={"topGames": [{"white": {"name": "Carlsen"}}]})

    monkeypatch.setattr(lichess_api.requests, "get", fake_get)
    out = lichess_api.fetch("explorer.lichess.ovh", "lichess", {"play": "e2e4"})

    assert captured["url"] == "https://explorer.lichess.ovh/lichess"
    assert captured["params"] == {"play": "e2e4"}
    assert out["topGames"][0]["white"]["name"] == "Carlsen"


def test_http_error_raises(monkeypatch):
    monkeypatch.setattr(lichess_api.requests, "get",
                        lambda *a, **k: _FakeResp(status=404, text="nope"))
    with pytest.raises(lichess_api.LichessError):
        lichess_api.fetch("lichess.org", "/api/user/nobody")


def test_non_json_returns_text(monkeypatch):
    monkeypatch.setattr(lichess_api.requests, "get",
                        lambda *a, **k: _FakeResp(text="1. e4 e5", ctype="application/x-chess-pgn"))
    out = lichess_api.fetch("lichess.org", "/game/export/abc")
    assert out == "1. e4 e5"
