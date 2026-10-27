"""tests/test_channel_stats.py — YouTube Data API channel ribbon (network mocked)."""

import json
import os

from channel_stats import get_channel_stats, get_video_stats, ChannelStats


def test_missing_credentials_returns_none(tmp_path):
    assert get_channel_stats("", "UC123", cache_dir=str(tmp_path)) is None
    assert get_channel_stats("key", "", cache_dir=str(tmp_path)) is None


def test_fresh_cache_is_used_without_network_call(tmp_path, monkeypatch):
    cache_dir = str(tmp_path)
    cache_path = os.path.join(cache_dir, "UC123.json")
    os.makedirs(cache_dir, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump({"subscriber_count": 1000, "view_count": 5000, "fetched_at": 0.0}, f)

    def _boom(*a, **kw):
        raise AssertionError("should not hit network when cache is fresh")

    monkeypatch.setattr("time.time", lambda: 100.0)  # within ttl of fetched_at=0 if ttl huge
    import requests
    monkeypatch.setattr(requests, "get", _boom)

    result = get_channel_stats("key", "UC123", cache_dir=cache_dir, ttl_seconds=1_000_000)
    assert result == ChannelStats(subscriber_count=1000, view_count=5000, fetched_at=0.0)


def test_stale_cache_triggers_refetch(tmp_path, monkeypatch):
    cache_dir = str(tmp_path)
    cache_path = os.path.join(cache_dir, "UC123.json")
    os.makedirs(cache_dir, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump({"subscriber_count": 1, "view_count": 1, "fetched_at": 0.0}, f)

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"items": [{"statistics": {"subscriberCount": "999", "viewCount": "8888"}}]}

    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _Resp())
    monkeypatch.setattr("os.path.getmtime", lambda p: 0.0)
    monkeypatch.setattr("time.time", lambda: 10_000_000.0)

    result = get_channel_stats("key", "UC123", cache_dir=cache_dir, ttl_seconds=60)
    assert result.subscriber_count == 999
    assert result.view_count == 8888


def test_network_failure_falls_back_to_stale_cache(tmp_path, monkeypatch):
    cache_dir = str(tmp_path)
    cache_path = os.path.join(cache_dir, "UC123.json")
    os.makedirs(cache_dir, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump({"subscriber_count": 42, "view_count": 42, "fetched_at": 0.0}, f)

    import requests

    def _boom(*a, **kw):
        raise ConnectionError("down")

    monkeypatch.setattr(requests, "get", _boom)
    monkeypatch.setattr("os.path.getmtime", lambda p: 0.0)
    monkeypatch.setattr("time.time", lambda: 10_000_000.0)  # way past ttl for the "fresh" check

    result = get_channel_stats("key", "UC123", cache_dir=cache_dir, ttl_seconds=60)
    # falls back to stale cache (ttl_seconds=inf on the fallback read) rather than raising
    assert result.subscriber_count == 42


def test_video_stats_missing_credentials_returns_none():
    assert get_video_stats("", "vid123") is None
    assert get_video_stats("key", "") is None


def test_video_stats_parses_counts(monkeypatch):
    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"items": [{"statistics": {
                "viewCount": "1234", "likeCount": "56", "commentCount": "7"}}]}

    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _Resp())

    result = get_video_stats("key", "vid123")
    assert result.view_count == 1234
    assert result.like_count == 56
    assert result.comment_count == 7


def test_video_stats_unknown_id_returns_none(monkeypatch):
    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"items": []}

    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _Resp())
    assert get_video_stats("key", "nope") is None


def test_video_stats_network_failure_returns_none(monkeypatch):
    import requests

    def _boom(*a, **kw):
        raise ConnectionError("down")

    monkeypatch.setattr(requests, "get", _boom)
    assert get_video_stats("key", "vid123") is None
