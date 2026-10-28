from chesscode.stages.metadata import build_description, pick_title

def test_description_ends_with_ccid():
    assert build_description("Hook",[{"title":"Opening","start_ms":0}],{"white":{"name":"A"},"black":{"name":"B"},"event":"Event","date":"2020","result":"1-0","opening":"Open","source":"lichess"},"Legendary",[],"cc-2026-0001-en").endswith("ccid: cc-2026-0001-en")

def test_description_chapters_start_0000():
    result=build_description("Hook",[{"title":"Opening","start_ms":0}],{},"S",[],"id")
    assert "00:00 Opening" in result

def test_short_hash_preserves_footer():
    assert build_description("Hook",[],{},"S",[],"cc-2026-5001-en").endswith("ccid: cc-2026-5001-en")
    assert "#Shorts" in build_description("Hook",[],{},"S",[],"cc-2026-5001-en")

def test_title_rejects_all_caps_and_long():
    assert pick_title(["THIS IS BAD", "x"*71, "A clever chess story"], lambda titles: titles[0]) == "A clever chess story"


import json
import shutil
from pathlib import Path

import pytest
import yaml

from chesscode.context import Context, StageError
from chesscode.stages import metadata

ROOT = Path(__file__).resolve().parents[2]


def metadata_ctx(tmp_path, video_id="cc-2026-0001-en", games=None):
    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "config", repo / "config")
    (repo / "content").mkdir()
    games = games or [{"game_no": 1, "series": "legendary_games", "tier": "floor"}]
    (repo / "content/games.yaml").write_text(yaml.safe_dump(games))
    spec = tmp_path / "spec"
    spec.mkdir()
    (spec / "game.json").write_text(json.dumps({"series": "legendary_games", "tier": "floor", "source": "local", "white": {"name": "A"}, "black": {"name": "B"}}))
    (spec / "script.json").write_text(json.dumps({"titles": ["First idea", "Second idea", "Third idea"], "hook": "Hook."}))
    (spec / "timeline.json").write_text(json.dumps({"chapters": [{"title": "Opening", "start_ms": 0}]}))
    return Context(video_id, spec, repo, {}, "en", "studio")


def test_title_comes_from_the_scorer_and_credits_are_in_the_description(tmp_path, monkeypatch):
    ctx = metadata_ctx(tmp_path)
    monkeypatch.setattr(metadata.llm, "complete_json", lambda *args: {"best": 2})
    metadata.run(ctx)
    result = json.loads((ctx.spec_dir / "metadata.json").read_text(encoding="utf-8"))
    assert result["title"] == "Third idea"
    assert "rhosgfx" in result["description"]


def test_scorer_index_out_of_range_stops(tmp_path, monkeypatch):
    ctx = metadata_ctx(tmp_path)
    monkeypatch.setattr(metadata.llm, "complete_json", lambda *args: {"best": 9})
    with pytest.raises(StageError, match="index 9"):
        metadata.run(ctx)


def test_no_slot_error_gives_the_calendar_reason(tmp_path, monkeypatch):
    games = [{"game_no": i, "series": "legendary_games", "tier": "floor"} for i in range(1, 4)]
    ctx = metadata_ctx(tmp_path, "cc-2026-0003-en", games)
    monkeypatch.setattr(metadata.llm, "complete_json", lambda *args: {"best": 0})
    with pytest.raises(StageError, match="series rule"):
        metadata.run(ctx)
