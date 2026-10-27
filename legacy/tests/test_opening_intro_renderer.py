"""tests/test_opening_intro_renderer.py — opening intro SVG card sequence."""

import os

from scene_renderer import FORMATS
from opening_stats import OpeningStats
from opening_intro_renderer import (
    OpeningIntroData, render_intro_sequence, _build_svg, _stagger,
)


def _data(**kw):
    base = dict(
        opening_name="Sicilian Najdorf", eco="B90",
        tagline="The sharpest response to 1.e4",
        moves="1.e4 c5 2.Nf3 d6",
        opening_stats=OpeningStats("Sicilian Najdorf", 45.0, 30.0, 25.0, 128456),
        famous_players=["Bobby Fischer", "Garry Kasparov"],
        players_note="A favourite of world champions",
    )
    base.update(kw)
    return OpeningIntroData(**base)


def test_sequence_returns_frames_and_durations_sum_to_duration(tmp_path):
    paths, durs = render_intro_sequence(
        _data(), FORMATS["hd"], out_dir=str(tmp_path / "frames"),
        game_id="t", duration=6.5, cache_dir=str(tmp_path / "cache"))
    assert len(paths) == len(durs) >= 5
    assert all(os.path.exists(p) for p in paths)
    assert abs(sum(durs) - 6.5) < 1e-6


def test_missing_players_and_stats_still_render(tmp_path):
    paths, durs = render_intro_sequence(
        _data(famous_players=[], opening_stats=None, players_note=""),
        FORMATS["shorts"], out_dir=str(tmp_path / "frames"),
        game_id="t2", duration=5.0, cache_dir=str(tmp_path / "cache"))
    assert len(paths) >= 5
    assert all(os.path.exists(p) for p in paths)


def test_svg_includes_players_when_present_and_omits_when_absent():
    svg = _build_svg(_data(), FORMATS["hd"], eased=1.0)
    assert "Bobby Fischer" in svg
    assert "CHAMPIONED BY" in svg

    svg2 = _build_svg(_data(famous_players=[]), FORMATS["hd"], eased=1.0)
    assert "CHAMPIONED BY" not in svg2


def test_svg_omits_stats_bar_when_stats_none():
    svg = _build_svg(_data(opening_stats=None), FORMATS["hd"], eased=1.0)
    assert "games analyzed" not in svg


def test_stagger_clamps():
    assert _stagger(0.0, 0.2, 0.6) == 0.0
    assert _stagger(1.0, 0.2, 0.6) == 1.0
    assert 0.0 < _stagger(0.4, 0.2, 0.6) < 1.0
