"""tests/test_cache_utils.py — content-addressed file cache."""

import os

from cache_utils import cache_key, get_cached, put_cached


def test_cache_key_deterministic():
    assert cache_key("a", "b") == cache_key("a", "b")


def test_cache_key_distinguishes_part_boundaries():
    # "ab","c" vs "a","bc" must not collide (null-byte separator prevents this)
    assert cache_key("ab", "c") != cache_key("a", "bc")


def test_get_cached_miss_returns_none(tmp_path):
    assert get_cached(str(tmp_path), "deadbeef", ".mp3") is None


def test_put_then_get_cached_roundtrip(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("hello")
    cache_dir = str(tmp_path / "cache")

    dst = put_cached(cache_dir, "mykey", ".txt", str(src))

    assert os.path.exists(dst)
    assert dst == get_cached(cache_dir, "mykey", ".txt")
    with open(dst) as f:
        assert f.read() == "hello"


def test_put_cached_creates_missing_dir(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("x")
    cache_dir = str(tmp_path / "does" / "not" / "exist")

    dst = put_cached(cache_dir, "k", ".txt", str(src))

    assert os.path.exists(dst)
