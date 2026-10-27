"""tests/test_opening_stats.py — Lichess Opening Explorer stats (network mocked)."""

from opening_stats import _parse_explorer_payload, _san_to_uci_play_list, get_opening_stats


def test_san_to_uci_converts_moves():
    uci = _san_to_uci_play_list("1. e4 e5 2. Nf3 Nc6")
    assert uci == ["e2e4", "e7e5", "g1f3", "b8c6"]


def test_san_to_uci_empty_string_returns_empty():
    assert _san_to_uci_play_list("") == []
    assert _san_to_uci_play_list("   ") == []


def test_san_to_uci_stops_on_illegal_move_without_raising():
    uci = _san_to_uci_play_list("1. e4 e5 2. Qh5 Qh5")  # Qh5 illegal for black (own queen there)
    assert uci[:2] == ["e2e4", "e7e5"]


def test_san_to_uci_caps_at_max_plies():
    uci = _san_to_uci_play_list("1. e4 e5 2. Nf3 Nc6 3. Bb5 a6", max_plies=3)
    assert len(uci) == 3


def test_parse_explorer_payload_computes_percentages():
    stats = _parse_explorer_payload("Ruy Lopez", {"white": 50, "draws": 30, "black": 20}, min_games=5)
    assert stats.total_games == 100
    assert stats.white_win_pct == 50.0
    assert stats.draw_pct == 30.0
    assert stats.black_win_pct == 20.0


def test_parse_explorer_payload_below_min_games_returns_none():
    assert _parse_explorer_payload("Obscure Line", {"white": 1, "draws": 1, "black": 1}, min_games=5) is None


def test_parse_explorer_payload_malformed_returns_none():
    assert _parse_explorer_payload("X", {"white": "not-a-number"}, min_games=5) is None


def test_get_opening_stats_no_moves_returns_none(tmp_path):
    assert get_opening_stats("Unknown", moves_san="", cache_dir=str(tmp_path)) is None


def test_get_opening_stats_network_failure_returns_none(tmp_path, monkeypatch):
    import opening_stats as mod

    monkeypatch.setattr(mod, "_query_lichess_explorer", lambda *a, **kw: None)

    result = get_opening_stats("Sicilian", moves_san="1. e4 c5", cache_dir=str(tmp_path))
    assert result is None
