"""mcp_server.py — MCP server exposing ChessCode pipeline tools.

Run: python mcp_server.py
Configure in Claude Desktop (claude_desktop_config.json):
  {
    "mcpServers": {
      "chesscode": {
        "command": "python",
        "args": ["C:/path/to/chess channel/mcp_server.py"]
      }
    }
  }
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Dict, Optional, Any

# Always run relative to this file's directory so subprocess calls to main.py resolve correctly
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from config import cfg
from content_calendar import ContentCalendar
from job_monitor import PORT as MONITOR_PORT, start_monitor_server
from job_registry import JobRegistry
from startup_validator import validate_startup, print_startup_summary, StartupValidationError

__all__ = ["app", "main", "get_job_status"]

logger = logging.getLogger(__name__)

app = Server(
    "chesscode",
    version="1.0.0",
    instructions=(
        "ChessCode — AI chess commentary video generator. Creates YouTube-style chess "
        "analysis videos: game breakdowns with Stockfish evaluation and move annotations, "
        "opening theory explainers, and trap/tactics Shorts. Handles PGN parsing, "
        "natural-voice TTS narration, animated board rendering with best/threat/defend "
        "arrows, a talking-pawn avatar, animated stats intros, and optional YouTube upload. "
        "Use render_video for a fully-scripted game (PGN + commentary you write), "
        "analyze_game for automatic Stockfish-driven analysis of a raw PGN, and "
        "generate_opening_video for an opening-theory explainer video."
    ),
)

# Bounded, thread-safe job registry: job_id → {proc, log_path, log_f, title, hindi, avatar, upload}
# Automatically archives completed jobs and caps history/queue size (see job_registry.py) —
# a plain dict here would grow forever across a long-running server process.
_registry = JobRegistry()


def _count_main_line_plies(pgn_text: str) -> Optional[int]:
    """Count half-moves (plies) in the PGN main line. None if the PGN won't parse."""
    import io as _io
    import chess.pgn
    try:
        game = chess.pgn.read_game(_io.StringIO(pgn_text))
        if game is None:
            return None
        return sum(1 for _ in game.mainline_moves())
    except Exception:
        return None


def _launch_job(
    cmd: list[str],
    log_dir: str = "logs",
    job_id: Optional[str] = None,
    **meta: Any
) -> Dict[str, Any]:
    """
    Start cmd as a background process, stream output to a log file, return job info immediately.
    
    Args:
       cmd: Command and arguments to run
       log_dir: Directory for log files
       job_id: Optional job ID (generated if not provided)
       **meta: Additional metadata to store with job (title, hindi, avatar, upload, etc.)
    
    Returns:
       Dictionary with job_id, log path, PID, status, and monitor URL
    
    Raises:
       RuntimeError: If the job queue is full or the process fails to start
    """
    if _registry.get_queue_status()["queue_full"]:
       raise RuntimeError(
           f"Job queue full (max {_registry.max_queue}). "
           "Wait for a running job to finish before starting another."
       )

    os.makedirs(log_dir, exist_ok=True)
    if job_id is None:
       job_id = str(uuid.uuid4())[:8]

    # Let main.py know its own job_id so it can write logs/<job_id>_stages.json —
    # a structured, non-log-scraped progress side channel for get_job_status.
    cmd = [*cmd, "--job-id", job_id]

    log_path = os.path.join(log_dir, f"{job_id}.log")
    try:
       log_f = open(log_path, "w", encoding="utf-8")
    except IOError as e:
       logger.error(f"Failed to open log file {log_path}: {e}")
       raise RuntimeError(f"Cannot create log file: {e}")
    
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    
    try:
       proc = subprocess.Popen(
           cmd,
           stdout=log_f,
           stderr=subprocess.STDOUT,
           env=env,
           text=True,
       )
       logger.info(f"[{job_id}] Started process {proc.pid}: {' '.join(cmd)}")
    except Exception as e:
       log_f.close()
       logger.error(f"Failed to start process for job {job_id}: {e}")
       raise RuntimeError(f"Failed to start job: {e}")
    
    _registry.add(job_id, {"proc": proc, "log_path": log_path, "log_f": log_f, **meta})


    monitor_url = f"http://localhost:{MONITOR_PORT}/job/{job_id}"
    return {
       "job_id": job_id,
       "log": log_path,
       "pid": proc.pid,
       "status": "running",
       "monitor_url": monitor_url,
       "hint": "Watch monitor_url in a browser for live progress. Don't poll get_job_status repeatedly — check it once near the end if you need the final result path.",
    }


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_queue",
            description="Get the current content queue and scheduled uploads.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="add_to_queue",
            description="Add a chess video to the content generation queue.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content_type": {
                        "type": "string",
                        "description": "Type of content: 'game', 'opening', or 'trap'",
                        "enum": ["game", "opening", "trap"],
                    },
                    "content_id": {
                        "type": "string",
                        "description": "PGN file path for games, opening name for openings/traps",
                    },
                    "title": {
                        "type": "string",
                        "description": "Human-readable title for the video",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority 1-10 (higher = processed sooner). Default: 5",
                        "default": 5,
                    },
                },
                "required": ["content_type", "content_id", "title"],
            },
        ),
        Tool(
            name="run_next",
            description="Process the next pending item in the content queue immediately.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="analyze_game",
            description=(
                "Generate a chess analysis video for a PGN game string. "
                "Returns a job_id and monitor_url immediately — open monitor_url in a "
                "browser for a live progress bar/log/chime. Don't poll get_job_status "
                "repeatedly; check it once near the end if you need the final result."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pgn": {
                        "type": "string",
                        "description": "PGN game text to analyze",
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional title for the video",
                        "default": "Game Analysis",
                    },
                },
                "required": ["pgn"],
            },
        ),
        Tool(
            name="generate_opening_video",
            description=(
                "Generate an educational opening theory video with a rich animated "
                "intro card (opening name, ECO, win/draw/loss stats, and the famous "
                "players who championed it).\n\n"
                "SUPPLY famous_players yourself — pick the iconic grandmasters most "
                "associated with this opening (most-famous first). If unsure, call the "
                "fetch_lichess tool first (Opening Explorer topGames) to source real "
                "names, then pass the best-known ones here.\n\n"
                "Returns a job_id and monitor_url immediately — open monitor_url in a "
                "browser for a live progress bar/log/chime. Don't poll get_job_status "
                "repeatedly; check it once near the end if you need the final result."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "opening_name": {
                        "type": "string",
                        "description": "Name of the chess opening (e.g. 'Sicilian Najdorf')",
                    },
                    "famous_players": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Iconic players who championed this opening, most-famous "
                            "first, up to 5 (e.g. ['Bobby Fischer','Garry Kasparov',"
                            "'Miguel Najdorf']). Shown as pills on the intro card."
                        ),
                    },
                    "players_note": {
                        "type": "string",
                        "description": (
                            "Optional one-line context under the players (e.g. "
                            "'A favourite of world champions')."
                        ),
                    },
                    "shorts": {
                        "type": "boolean",
                        "description": "Render in vertical Shorts format (1080×1920).",
                        "default": False,
                    },
                    "legend_name": {
                        "type": "string",
                        "description": (
                            "Chess legend to feature in the sidebar's legend card "
                            "(e.g. 'Garry Kasparov'). Omit to use the rotating default."
                        ),
                    },
                    "legend_title": {
                        "type": "string",
                        "description": "Legend's defining title/era. Pass with legend_name.",
                    },
                    "legend_fact": {
                        "type": "string",
                        "description": "1-2 short factual sentences about the legend. Pass with legend_name.",
                    },
                },
                "required": ["opening_name"],
            },
        ),
        Tool(
            name="fetch_lichess",
            description=(
                "Read-only GET against the official Lichess APIs. Use it to source "
                "data for videos — most usefully the Opening Explorer, whose response "
                "includes a topGames array with real player names for a line.\n\n"
                "Examples:\n"
                "  • Opening Explorer for 1.e4 c5: host='explorer.lichess.ovh', "
                "path='/lichess', params={'play':'e2e4,c7c5'} (moves are UCI, comma-"
                "separated). Returns white/draws/black counts, moves, and topGames[] "
                "with .white.name / .black.name.\n"
                "  • Player profile: host='lichess.org', path='/api/user/DrNykterstein'.\n"
                "Only the three official Lichess hosts are allowed."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "enum": ["lichess.org", "explorer.lichess.ovh", "lichess.ovh"],
                        "default": "lichess.org",
                        "description": "Which Lichess host to query.",
                    },
                    "path": {
                        "type": "string",
                        "description": "URL path, e.g. '/api/opening/explorer' or '/lichess' or '/api/user/<name>'.",
                    },
                    "params": {
                        "type": "object",
                        "description": "Optional query parameters as a JSON object.",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="render_video",
            description=(
                "Render a chess video given a PGN and per-move commentary. "
                "YOU write the PGN (with variations) and the commentary, then call this tool.\n\n"
                "PGN with variations syntax:\n"
                "  1. e4 e5 (1... c5 {Sicilian - more aggressive} 2. Nf3 d6) "
                "2. Nf3 Nc6 3. Bb5 {Ruy Lopez}\n"
                "Use {...} for inline move comments. Use (...) for alternate lines.\n"
                "Only the main line is rendered on the board; mention variations in commentary prose.\n\n"
                "COMMENTARY CONTRACT (enforced — the render is REJECTED if you break it):\n"
                "  • intro: one opening sentence, shown over the starting position.\n"
                "  • move_comments: an array with EXACTLY ONE sentence per move in the "
                "main line, in order. The array length MUST equal the number of half-moves "
                "(plies) in the PGN main line. Every move gets its own explanation — it is "
                "narrated AND burned in as an on-screen caption on that move's frame.\n"
                "  • conclusion: one closing sentence, shown over the final position.\n\n"
                "Example — PGN '1. e4 e5 2. Nf3' has 3 plies (e4, e5, Nf3), so move_comments "
                "must have 3 entries:\n"
                "  intro: 'A classic Italian setup begins.'\n"
                "  move_comments: ['White claims the center with e4.', 'Black mirrors with e5.', "
                "'Nf3 develops and eyes the e5 pawn.']\n"
                "  conclusion: 'A balanced position with chances for both sides.'\n\n"
                "Returns a job_id and monitor_url immediately — open monitor_url in a browser "
                "for a live progress bar/log/chime instead of polling. Only call get_job_status "
                "once near the end if you need the final result path.\n"
                "Workflow: construct PGN → count the main-line plies → write intro + one comment "
                "per ply + conclusion → call this tool."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pgn": {
                        "type": "string",
                        "description": (
                            "Full PGN text including headers. May include variations in "
                            "parentheses and {comments} on moves. Main line is rendered "
                            "on the board; variations can be referenced in your commentary."
                        ),
                    },
                    "intro": {
                        "type": "string",
                        "description": "One opening sentence, spoken and captioned over the starting position.",
                    },
                    "move_comments": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "One commentary sentence per main-line move (ply), in order. "
                            "Array length MUST equal the number of plies in the PGN main line. "
                            "Each entry is narrated and shown as a caption on that move's frame. "
                            "Use natural punctuation for TTS pacing: commas for breath, "
                            "ellipsis (...) for dramatic pauses, ! for brilliant moves only. "
                            "Also provide Hindi versions of all commentary fields when hindi=true."
                        ),
                    },
                    "conclusion": {
                        "type": "string",
                        "description": "One closing sentence, spoken and captioned over the final position.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Video title",
                    },
                    "upload": {
                        "type": "boolean",
                        "description": "Whether to upload to YouTube after rendering",
                        "default": False,
                    },
                    "publish_at": {
                        "type": "string",
                        "description": "Schedule the YouTube publish for an ISO 8601 UTC "
                                       "datetime (e.g. 2026-07-20T09:00:00Z). Implies upload; "
                                       "the video stays private until this time.",
                    },
                    "hindi": {
                        "type": "boolean",
                        "description": "Also generate Hindi version",
                        "default": False,
                    },
                    "avatar": {
                        "type": "boolean",
                        "description": "Show talking pawn avatar overlay in video (default: True)",
                        "default": True,
                    },
                    "stats_intro": {
                        "type": "boolean",
                        "description": (
                            "Show animated stats intro card (ratings/opening stats/channel "
                            "stats) at video start (default: True)"
                        ),
                        "default": True,
                    },
                    "legend_name": {
                        "type": "string",
                        "description": (
                            "Chess legend to feature in the sidebar's legend card for this "
                            "video (e.g. 'Mikhail Tal'). Pick one relevant to the game/opening/"
                            "players — the actual player if they're a known legend, or one "
                            "whose style matches the game (e.g. Tal for a sacrificial attack). "
                            "Omit to use the built-in rotating default."
                        ),
                    },
                    "legend_title": {
                        "type": "string",
                        "description": "Legend's defining title/era, e.g. 'World Champion 1960-1961'. Pass with legend_name.",
                    },
                    "legend_fact": {
                        "type": "string",
                        "description": "1-2 short, factually-accurate sentences about the legend (~150 chars, wraps in the card). Pass with legend_name.",
                    },
                    "theme": {
                        "type": "string",
                        "enum": ["classic", "cyberpunk", "retro"],
                        "description": "Visual theme. classic=elegant wood, cyberpunk=neon tech, retro=arcade pixel.",
                        "default": "classic",
                    },
                    "intro_hi": {
                        "type": "string",
                        "description": "Hindi intro narration in Devanagari. Provide when hindi=true for native Hindi commentary.",
                        "default": "",
                    },
                    "move_comments_hi": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Per-move Hindi narration (Devanagari). One entry per PGN main-line ply. "
                            "Required when hindi=true for native Hindi commentary (not auto-translated)."
                        ),
                        "default": [],
                    },
                    "conclusion_hi": {
                        "type": "string",
                        "description": "Hindi conclusion narration in Devanagari. Provide when hindi=true.",
                        "default": "",
                    },
                    "coach_insights": {
                        "type": "array",
                        "description": (
                            "Per-move coach sidebar data from the sidebar_coach_prompt. "
                            "One object per PGN main-line ply. Each object has top_engine_moves + insights."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "top_engine_moves": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "san": {"type": "string"},
                                            "score_cp": {"type": "integer"},
                                            "rank": {"type": "integer"},
                                            "label": {"type": "string"},
                                        },
                                    },
                                },
                                "insights": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Exactly 3 strings with optional <b>HTML</b> tags, max 12 words each.",
                                },
                            },
                        },
                        "default": [],
                    },
                },
                "required": ["pgn", "intro", "move_comments", "conclusion", "title"],
            },
        ),
        Tool(
            name="get_job_status",
            description=(
                "Check the status of a background render/analysis job started by "
                "render_video, analyze_game, or generate_opening_video."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "job_id returned by the render/analyze tool",
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Last N lines of log to return (default: 50)",
                        "default": 50,
                    },
                },
                "required": ["job_id"],
            },
        ),
        Tool(
            name="cancel_job",
            description=(
                "Cancel a running background job by job_id: terminates the process, "
                "marks it cancelled in the registry, and best-effort cleans up its "
                "partial output directory. Safe to call on an already-finished or "
                "unknown job_id (returns a clean error, never raises)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "job_id returned by the render/analyze tool",
                    },
                },
                "required": ["job_id"],
            },
        ),
        Tool(
            name="get_api_key_status",
            description=(
                "Check which API keys/credentials the pipeline depends on are configured. "
                "Returns the .env file location and a set/missing status per key. Never "
                "reads or returns actual key values."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="generate_thumbnail",
            description=(
                "Generate a YouTube thumbnail via OpenAI's gpt-image-1 API and save it "
                "locally. Requires OPENAI_API_KEY to be configured — fails with a clear "
                "error if missing (never a raw exception trace, never falls back to "
                "browser automation or any other channel)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Video title — used to build the default prompt if prompt isn't given.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Custom image prompt. If omitted, built from title + channel style.",
                    },
                    "reference_image_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Local image paths for style consistency (uses the edits endpoint).",
                    },
                    "size": {
                        "type": "string",
                        "description": "Desired size, e.g. '1280x720' (default). Mapped to a supported gpt-image-1 size.",
                        "default": "1280x720",
                    },
                    "style_preset": {
                        "type": "string",
                        "description": "One of the built-in style presets to append to the prompt (e.g. 'joshila', 'minimal', 'dramatic').",
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="pull_stats",
            description=(
                "Pull live YouTube statistics via the Data API v3 (public stats only, "
                "uses YOUTUBE_API_KEY). Provide video_id, channel_id, or both:\n"
                "  • video_id → view/like/comment counts for that video.\n"
                "  • channel_id → subscriber/view/video counts for that channel. "
                "Omit channel_id to use the configured YOUTUBE_CHANNEL_ID.\n"
                "Use this after publishing to report performance. Returns a clean JSON "
                "error (never a key value) if YOUTUBE_API_KEY is missing or an id is "
                "unknown."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "YouTube video ID to pull view/like/comment counts for.",
                    },
                    "channel_id": {
                        "type": "string",
                        "description": (
                            "YouTube channel ID (UC...) to pull subscriber/view/video "
                            "counts for. Defaults to the configured YOUTUBE_CHANNEL_ID."
                        ),
                    },
                },
                "required": [],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    cal = ContentCalendar(cfg.db_path)

    if name == "get_queue":
        status = cal.get_status()
        return [TextContent(type="text", text=json.dumps(status, indent=2, default=str))]

    elif name == "add_to_queue":
        queue_id = cal.add(
            content_type=arguments["content_type"],
            content_id=arguments["content_id"],
            title=arguments["title"],
            priority=arguments.get("priority", 5),
        )
        return [TextContent(type="text", text=f"Added to queue with ID {queue_id}")]

    elif name == "run_next":
        from autonomous_runner import _run_scheduled_job
        # _run_scheduled_job() runs a full render synchronously; keep it off the MCP
        # event loop so the server stays responsive while it works.
        await asyncio.to_thread(_run_scheduled_job)
        return [TextContent(type="text", text="Job triggered. Check runner.log for output.")]

    elif name == "analyze_game":
        pgn_text = arguments["pgn"]
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        job_id = str(uuid.uuid4())[:8]
        pgn_path = os.path.join(log_dir, f"{job_id}_pgn.pgn")
        with open(pgn_path, "w", encoding="utf-8") as f:
            f.write(pgn_text)
        cmd = [sys.executable, "main.py", pgn_path]
        info = _launch_job(cmd, log_dir=log_dir, job_id=job_id, title=arguments.get("title", "Game Analysis"))
        return [TextContent(type="text", text=json.dumps(info, indent=2))]

    elif name == "generate_opening_video":
        opening_name = arguments["opening_name"]
        shorts = arguments.get("shorts", False)
        legend_name = arguments.get("legend_name")
        legend_title = arguments.get("legend_title")
        legend_fact = arguments.get("legend_fact")

        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        job_id = str(uuid.uuid4())[:8]
        payload = {
            "famous_players": arguments.get("famous_players", []) or [],
            "players_note": arguments.get("players_note", "") or "",
        }
        payload_path = os.path.join(log_dir, f"{job_id}_opening.json")
        with open(payload_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

        cmd = [sys.executable, "main.py", "--opening", opening_name,
               "--opening-payload-json", payload_path]
        if shorts:
            cmd.append("--shorts")
        if legend_name:
            cmd += ["--legend-name", legend_name]
            if legend_title:
                cmd += ["--legend-title", legend_title]
            if legend_fact:
                cmd += ["--legend-fact", legend_fact]

        info = _launch_job(cmd, log_dir=log_dir, job_id=job_id, title=opening_name)
        return [TextContent(type="text", text=json.dumps(info, indent=2))]

    elif name == "fetch_lichess":
        import lichess_api
        host = arguments.get("host", "lichess.org")
        path = arguments["path"]
        params = arguments.get("params") or {}
        try:
            data = lichess_api.fetch(host, path, params)
        except lichess_api.LichessError as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]
        if isinstance(data, (dict, list)):
            text = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            text = str(data)
        if len(text) > 40000:
            text = text[:40000] + "\n… [truncated]"
        return [TextContent(type="text", text=text)]

    elif name == "render_video":
        pgn_text = arguments["pgn"]
        intro = arguments["intro"]
        move_comments = arguments["move_comments"]
        conclusion = arguments["conclusion"]
        title = arguments["title"]
        upload = arguments.get("upload", False)
        publish_at = arguments.get("publish_at", "") or ""
        hindi = arguments.get("hindi", False)
        avatar = arguments.get("avatar", True)
        stats_intro = arguments.get("stats_intro", True)
        legend_name = arguments.get("legend_name")
        legend_title = arguments.get("legend_title")
        legend_fact = arguments.get("legend_fact")
        theme = arguments.get("theme", "classic")
        intro_hi = arguments.get("intro_hi", "")
        move_comments_hi = arguments.get("move_comments_hi", [])
        conclusion_hi = arguments.get("conclusion_hi", "")
        coach_insights = arguments.get("coach_insights", [])

        # ── Enforce the per-move commentary contract ─────────────────────────
        ply_count = _count_main_line_plies(pgn_text)
        if not ply_count:
            return [TextContent(type="text", text=(
                "render_video rejected: the PGN has no readable main-line moves. "
                "Check the PGN syntax and resubmit."))]
        if not isinstance(move_comments, list) or len(move_comments) != ply_count:
            got = len(move_comments) if isinstance(move_comments, list) else "not-a-list"
            return [TextContent(type="text", text=(
                f"render_video rejected: move_comments must have exactly one entry per "
                f"main-line move. The PGN has {ply_count} plies but move_comments has {got}. "
                f"Write exactly {ply_count} comments (one per move, in order), then resubmit."))]

        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        job_id = str(uuid.uuid4())[:8]
        pgn_path = os.path.join(log_dir, f"{job_id}_pgn.pgn")
        com_path = os.path.join(log_dir, f"{job_id}_com.json")

        with open(pgn_path, "w", encoding="utf-8") as f:
            f.write(pgn_text)
        with open(com_path, "w", encoding="utf-8") as f:
            json.dump({
                "intro": intro,
                "move_comments": move_comments,
                "conclusion": conclusion,
                "intro_hi": intro_hi,
                "move_comments_hi": move_comments_hi,
                "conclusion_hi": conclusion_hi,
                "coach_insights": coach_insights,
            }, f, ensure_ascii=False)

        cmd = [
            sys.executable, "main.py", pgn_path,
            "--no-claude",
            "--provided-commentary-json", com_path,
            "--provided-title", title,
            "--quality", "ultrafast",
        ]
        if upload:
            cmd.append("--upload")
        if publish_at:
            cmd += ["--publish-at", publish_at]
        if hindi:
            cmd.append("--hindi")
        if not avatar:
            cmd.append("--no-avatar")
        if not stats_intro:
            cmd.append("--no-stats-intro")
        if legend_name:
            cmd += ["--legend-name", legend_name]
            if legend_title:
                cmd += ["--legend-title", legend_title]
            if legend_fact:
                cmd += ["--legend-fact", legend_fact]
        if theme and theme != "classic":
            cmd += ["--theme", theme]

        info = _launch_job(cmd, log_dir=log_dir, job_id=job_id, title=title,
                            hindi=hindi, avatar=avatar, upload=upload)
        info["commentary_file"] = com_path

        return [TextContent(type="text", text=json.dumps(info, indent=2))]

    elif name == "get_job_status":
        job_id = arguments["job_id"]
        tail_n = int(arguments.get("tail", 50))
        
        job = _registry.get(job_id)

        if not job:
            return [TextContent(type="text", text=json.dumps({
                "error": f"Unknown job_id: {job_id}",
                "hint": "job_ids are only tracked for the current server session",
            }, indent=2))]

        rc = job["proc"].poll()
        status = "running" if rc is None else ("done" if rc == 0 else f"failed (exit {rc})")

        log_lines: list[str] = []
        log_path = job["log_path"]
        try:
            if os.path.exists(log_path):
                with open(log_path, encoding="utf-8", errors="replace") as f:
                    log_lines = f.readlines()[-tail_n:]
        except IOError as e:
            logger.warning(f"Failed to read log file {log_path}: {e}")

        # Structured progress side channel written explicitly by main.py at each phase
        # boundary (see main.py:_write_stage_status) — NOT derived from log_lines above.
        # Missing/corrupt file (job hasn't started writing yet, or was launched without
        # a job_id) is tolerated: stages just comes back empty.
        stages: list[dict] = []
        stages_path = os.path.join(os.path.dirname(log_path), f"{job_id}_stages.json")
        try:
            if os.path.exists(stages_path):
                with open(stages_path, encoding="utf-8") as f:
                    stages = json.load(f).get("stages", [])
        except (IOError, ValueError) as e:
            logger.warning(f"Failed to read stage status file {stages_path}: {e}")

        return [TextContent(type="text", text=json.dumps({
            "job_id": job_id,
            "status": status,
            "stages": stages,
            "log_tail": "".join(log_lines),
        }, indent=2))]

    elif name == "cancel_job":
        job_id = arguments["job_id"]
        result = _registry.cancel(job_id, output_dir=cfg.output_dir)
        if result is None:
            return [TextContent(type="text", text=json.dumps({
                "error": f"Unknown job_id: {job_id}",
                "hint": "job_ids are only tracked for the current server session",
            }, indent=2))]
        # proc/log_f aren't JSON-serializable — strip before returning
        safe_result = {k: v for k, v in result.items() if k not in ("proc", "log_f")}
        return [TextContent(type="text", text=json.dumps(safe_result, indent=2, default=str))]

    elif name == "get_api_key_status":
        try:
            from youtube_uploader import TOKEN_FILE
            env_path = Path(__file__).parent / ".env"
            client_secret_path = Path(__file__).parent / "client_secret.json"
            token_path = Path(__file__).parent / TOKEN_FILE
            keys = {
                "ANTHROPIC_API_KEY": "set" if cfg.has_anthropic else "missing",
                "ELEVENLABS_API_KEY": "set" if cfg.has_elevenlabs else "missing",
                "LEONARDO_API_KEY": "set" if cfg.has_leonardo else "missing",
                "OPENAI_API_KEY": "set" if cfg.has_openai else "missing",
                "LICHESS_TOKEN": "set" if cfg.has_lichess else "missing",
                "YOUTUBE_API_KEY": "set" if cfg.youtube_api_key else "missing",
                "YOUTUBE_CHANNEL_ID": "set" if cfg.youtube_channel_id else "missing",
                "YOUTUBE_OAUTH_client_secret.json": "set" if client_secret_path.exists() else "missing",
                "YOUTUBE_OAUTH_token.pickle": "set" if token_path.exists() else "missing",
            }
            result = {
                "config_location": str(env_path),
                "keys": keys,
                "note": "VIDIQ is not integrated in this project — no VIDIQ credentials are read.",
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception:
            return [TextContent(type="text", text=json.dumps({
                "error": "Failed to check API key status",
            }, indent=2))]

    elif name == "generate_thumbnail":
        from thumbnail_openai import generate_thumbnail
        try:
            info = generate_thumbnail(
                title=arguments["title"],
                prompt=arguments.get("prompt", ""),
                reference_image_paths=arguments.get("reference_image_paths"),
                size=arguments.get("size", "1280x720"),
                style_preset=arguments.get("style_preset", ""),
            )
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]
        return [TextContent(type="text", text=json.dumps(info, indent=2))]

    elif name == "pull_stats":
        from channel_stats import get_channel_stats, get_video_stats

        if not cfg.youtube_api_key:
            return [TextContent(type="text", text=json.dumps({
                "error": "YOUTUBE_API_KEY not configured — cannot pull YouTube stats.",
            }, indent=2))]

        video_id = arguments.get("video_id", "") or ""
        channel_id = arguments.get("channel_id", "") or cfg.youtube_channel_id or ""

        if not video_id and not channel_id:
            return [TextContent(type="text", text=json.dumps({
                "error": (
                    "Provide a video_id and/or a channel_id (or configure "
                    "YOUTUBE_CHANNEL_ID for the channel default)."
                ),
            }, indent=2))]

        result: Dict[str, Any] = {}
        if video_id:
            vs = get_video_stats(cfg.youtube_api_key, video_id)
            result["video"] = (
                {"video_id": video_id, "view_count": vs.view_count,
                 "like_count": vs.like_count, "comment_count": vs.comment_count}
                if vs else {"video_id": video_id, "error": "no stats found for this video_id"}
            )
        if channel_id:
            cs = get_channel_stats(cfg.youtube_api_key, channel_id)
            result["channel"] = (
                {"channel_id": channel_id, "subscriber_count": cs.subscriber_count,
                 "view_count": cs.view_count, "video_count": cs.video_count}
                if cs else {"channel_id": channel_id, "error": "no stats found for this channel_id"}
            )
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main() -> None:
    """Initialize MCP server with startup validation."""
    # Validate configuration before starting
    try:
        results = validate_startup()
        print_startup_summary(results)
    except StartupValidationError as e:
        logger.error(f"Startup validation failed: {e}")
        print(f"❌ Startup failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Start monitor server in background daemon thread
    threading.Thread(target=start_monitor_server, args=(_registry,), daemon=True).start()
    logger.info("Job monitor server started on port %d", MONITOR_PORT)
    
    # Start MCP server
    logger.info("Starting ChessCode MCP server...")
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("mcp_server.log", encoding="utf-8"),
        ],
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MCP server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"MCP server error: {e}")
        sys.exit(1)
