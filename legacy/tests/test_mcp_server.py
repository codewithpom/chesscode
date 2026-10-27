"""tests/test_mcp_server.py — contract tests for the MCP tool layer.

No real render ever happens here: subprocess.Popen is monkeypatched (see the
no_subprocess fixture in conftest.py) so call_tool() only proves it builds the
right main.py command line, never that main.py itself works end to end.
"""

import asyncio
import json
import os

import mcp_server


def _run(coro):
    return asyncio.run(coro)


def test_list_tools_exposes_expected_tool_names():
    tools = _run(mcp_server.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "get_queue", "add_to_queue", "run_next",
        "analyze_game", "generate_opening_video", "render_video", "get_job_status",
        "fetch_lichess", "cancel_job", "get_api_key_status", "generate_thumbnail", "pull_stats",
    }


def test_render_video_schema_requires_per_move_contract():
    tools = _run(mcp_server.list_tools())
    render_video = next(t for t in tools if t.name == "render_video")
    assert set(render_video.inputSchema["required"]) == {
        "pgn", "intro", "move_comments", "conclusion", "title"}


def test_pull_stats_schema_accepts_optional_ids():
    tools = _run(mcp_server.list_tools())
    pull_stats = next(t for t in tools if t.name == "pull_stats")
    props = pull_stats.inputSchema["properties"]
    assert set(props) == {"video_id", "channel_id"}
    assert pull_stats.inputSchema.get("required", []) == []


def test_render_video_default_flags_are_on():
    tools = _run(mcp_server.list_tools())
    render_video = next(t for t in tools if t.name == "render_video")
    props = render_video.inputSchema["properties"]
    assert props["avatar"]["default"] is True
    assert props["stats_intro"]["default"] is True
    assert props["upload"]["default"] is False
    assert props["hindi"]["default"] is False


def _cmd(no_subprocess):
    """Return the last captured command list (as strings) after a call_tool run."""
    assert no_subprocess, "no subprocess call captured"
    return no_subprocess[-1]["cmd"]


def test_render_video_builds_no_avatar_flag(no_subprocess):
    _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T", "avatar": False,
    }))
    assert "--no-avatar" in _cmd(no_subprocess)


def test_render_video_omits_no_avatar_flag_when_avatar_true(no_subprocess):
    _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T", "avatar": True,
    }))
    assert "--no-avatar" not in _cmd(no_subprocess)


def test_render_video_builds_no_stats_intro_flag(no_subprocess):
    _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T", "stats_intro": False,
    }))
    assert "--no-stats-intro" in _cmd(no_subprocess)


def test_render_video_builds_upload_and_hindi_flags(no_subprocess):
    _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T", "upload": True, "hindi": True,
    }))
    cmd = _cmd(no_subprocess)
    assert "--upload" in cmd
    assert "--hindi" in cmd


def test_render_video_builds_publish_at_flag(no_subprocess):
    _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T",
        "publish_at": "2026-07-20T09:00:00Z",
    }))
    cmd = _cmd(no_subprocess)
    assert "--publish-at" in cmd
    assert "2026-07-20T09:00:00Z" in cmd


def test_render_video_omits_publish_at_flag_by_default(no_subprocess):
    _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T",
    }))
    assert "--publish-at" not in _cmd(no_subprocess)


def test_render_video_passes_legend_fields(no_subprocess):
    _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T",
        "legend_name": "Mikhail Tal", "legend_title": "World Champion 1960-1961",
        "legend_fact": "The Magician from Riga.",
    }))
    cmd = _cmd(no_subprocess)
    assert "--legend-name" in cmd
    assert "Mikhail Tal" in cmd
    assert "--legend-title" in cmd
    assert "--legend-fact" in cmd


def test_render_video_omits_legend_title_fact_without_legend_name(no_subprocess):
    _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T",
    }))
    cmd = _cmd(no_subprocess)
    assert "--legend-name" not in cmd
    assert "--legend-title" not in cmd


def test_render_video_defaults_have_no_optional_flags(no_subprocess):
    _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T",
    }))
    cmd = _cmd(no_subprocess)
    assert "--no-avatar" not in cmd
    assert "--no-stats-intro" not in cmd
    assert "--upload" not in cmd
    assert "--hindi" not in cmd


def test_analyze_game_returns_job_info(no_subprocess):
    result = _run(mcp_server.call_tool("analyze_game", {"pgn": "1. e4 e5", "title": "My Game"}))
    info = json.loads(result[0].text)
    assert "job_id" in info
    assert info["status"] == "running"


def test_get_api_key_status_reports_presence_without_leaking_values(monkeypatch):
    monkeypatch.setattr(mcp_server.cfg, "anthropic_api_key", "sk-super-secret-value")
    monkeypatch.setattr(mcp_server.cfg, "lichess_token", "")

    result = _run(mcp_server.call_tool("get_api_key_status", {}))
    info = json.loads(result[0].text)

    assert info["config_location"].endswith(".env")
    assert info["keys"]["ANTHROPIC_API_KEY"] == "set"
    assert info["keys"]["LICHESS_TOKEN"] == "missing"
    assert "sk-super-secret-value" not in result[0].text


def test_pull_stats_missing_api_key_returns_clean_error(monkeypatch):
    monkeypatch.setattr(mcp_server.cfg, "youtube_api_key", "")
    result = _run(mcp_server.call_tool("pull_stats", {"video_id": "vid1"}))
    info = json.loads(result[0].text)
    assert "error" in info and "YOUTUBE_API_KEY" in info["error"]


def test_pull_stats_no_ids_returns_error(monkeypatch):
    monkeypatch.setattr(mcp_server.cfg, "youtube_api_key", "key")
    monkeypatch.setattr(mcp_server.cfg, "youtube_channel_id", "")
    result = _run(mcp_server.call_tool("pull_stats", {}))
    info = json.loads(result[0].text)
    assert "error" in info


def test_pull_stats_returns_video_and_channel(monkeypatch):
    import channel_stats
    monkeypatch.setattr(mcp_server.cfg, "youtube_api_key", "key")
    monkeypatch.setattr(mcp_server.cfg, "youtube_channel_id", "UCdefault")
    monkeypatch.setattr(channel_stats, "get_video_stats", lambda k, v, **kw:
                        channel_stats.VideoStats(view_count=10, like_count=2,
                                                 comment_count=1, fetched_at=0.0))
    monkeypatch.setattr(channel_stats, "get_channel_stats", lambda k, c, **kw:
                        channel_stats.ChannelStats(subscriber_count=99, view_count=500,
                                                   fetched_at=0.0, video_count=7))

    result = _run(mcp_server.call_tool("pull_stats", {"video_id": "vid1"}))
    info = json.loads(result[0].text)
    assert info["video"]["view_count"] == 10
    assert info["video"]["like_count"] == 2
    # channel_id defaults to configured YOUTUBE_CHANNEL_ID
    assert info["channel"]["channel_id"] == "UCdefault"
    assert info["channel"]["subscriber_count"] == 99
    assert info["channel"]["video_count"] == 7


def test_get_job_status_unknown_job():
    result = _run(mcp_server.call_tool("get_job_status", {"job_id": "does-not-exist"}))
    info = json.loads(result[0].text)
    assert "error" in info


def test_get_job_status_running_job(no_subprocess):
    launch = _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T",
    }))
    job_id = json.loads(launch[0].text)["job_id"]

    status = _run(mcp_server.call_tool("get_job_status", {"job_id": job_id}))
    info = json.loads(status[0].text)
    assert info["status"] == "running"


def test_render_video_appends_job_id_flag(no_subprocess):
    launch = _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T",
    }))
    job_id = json.loads(launch[0].text)["job_id"]
    cmd = _cmd(no_subprocess)
    assert "--job-id" in cmd
    assert cmd[cmd.index("--job-id") + 1] == job_id


def test_get_job_status_includes_empty_stages_when_no_stages_file(no_subprocess):
    launch = _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T",
    }))
    job_id = json.loads(launch[0].text)["job_id"]

    status = _run(mcp_server.call_tool("get_job_status", {"job_id": job_id}))
    info = json.loads(status[0].text)
    assert info["stages"] == []


def test_get_job_status_reads_stages_file(no_subprocess, tmp_path):
    launch = _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T",
    }))
    job_id = json.loads(launch[0].text)["job_id"]

    # Simulate main.py's structured stage-progress side channel (written explicitly
    # by _write_stage_status at each phase boundary — never by log-text parsing).
    stages_payload = {
        "job_id": job_id,
        "stages": [
            {"name": "Stockfish analysis", "status": "done"},
            {"name": "Commentary (English)", "status": "done"},
            {"name": "TTS — English", "status": "running"},
            {"name": "Board frames", "status": "pending"},
            {"name": "Render — English", "status": "pending"},
            {"name": "Thumbnails", "status": "pending"},
        ],
    }
    stages_path = os.path.join("logs", f"{job_id}_stages.json")
    with open(stages_path, "w", encoding="utf-8") as f:
        json.dump(stages_payload, f)

    status = _run(mcp_server.call_tool("get_job_status", {"job_id": job_id}))
    info = json.loads(status[0].text)
    assert info["job_id"] == job_id
    assert "status" in info
    assert "log_tail" in info
    assert info["stages"] == stages_payload["stages"]


def test_get_job_status_tolerates_corrupt_stages_file(no_subprocess):
    launch = _run(mcp_server.call_tool("render_video", {
        "pgn": "1. e4 e5", "intro": "Opening.", "move_comments": ["White plays e4.", "Black plays e5."], "conclusion": "Done.", "title": "T",
    }))
    job_id = json.loads(launch[0].text)["job_id"]

    stages_path = os.path.join("logs", f"{job_id}_stages.json")
    with open(stages_path, "w", encoding="utf-8") as f:
        f.write("{not valid json")

    status = _run(mcp_server.call_tool("get_job_status", {"job_id": job_id}))
    info = json.loads(status[0].text)
    assert info["stages"] == []


def test_generate_opening_video_passes_payload_and_players(no_subprocess):
    _run(mcp_server.call_tool("generate_opening_video", {
        "opening_name": "Sicilian Najdorf",
        "famous_players": ["Bobby Fischer", "Garry Kasparov"],
        "players_note": "A world-champion favourite",
        "shorts": True,
    }))
    cmd = _cmd(no_subprocess)
    assert "--opening" in cmd and "Sicilian Najdorf" in cmd
    assert "--shorts" in cmd
    assert "--opening-payload-json" in cmd
    payload_path = cmd[cmd.index("--opening-payload-json") + 1]
    with open(payload_path, encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["famous_players"] == ["Bobby Fischer", "Garry Kasparov"]
    assert payload["players_note"] == "A world-champion favourite"


def test_generate_opening_video_omits_shorts_by_default(no_subprocess):
    _run(mcp_server.call_tool("generate_opening_video", {"opening_name": "Italian Game"}))
    cmd = _cmd(no_subprocess)
    assert "--shorts" not in cmd
    assert "--opening-payload-json" in cmd


def test_fetch_lichess_rejects_bad_host():
    result = _run(mcp_server.call_tool("fetch_lichess", {
        "host": "evil.com", "path": "/x",
    }))
    info = json.loads(result[0].text)
    assert "error" in info


def test_fetch_lichess_returns_json(monkeypatch):
    import lichess_api
    monkeypatch.setattr(lichess_api, "fetch",
                        lambda host, path, params: {"topGames": [{"white": {"name": "Carlsen"}}]})
    result = _run(mcp_server.call_tool("fetch_lichess", {
        "host": "explorer.lichess.ovh", "path": "/lichess", "params": {"play": "e2e4"},
    }))
    assert "Carlsen" in result[0].text


def test_unknown_tool_name_returns_error_text():
    result = _run(mcp_server.call_tool("not_a_real_tool", {}))
    assert "Unknown tool" in result[0].text


def test_add_to_queue_and_get_queue_roundtrip(tmp_path, monkeypatch):
    from config import cfg
    monkeypatch.setattr(cfg, "db_path", str(tmp_path / "test.db"))

    add_result = _run(mcp_server.call_tool("add_to_queue", {
        "content_type": "game", "content_id": "g.pgn", "title": "Queued Game",
    }))
    assert "Added to queue" in add_result[0].text

    queue_result = _run(mcp_server.call_tool("get_queue", {}))
    status = json.loads(queue_result[0].text)
    assert any(item["title"] == "Queued Game" for item in status["queue"])
