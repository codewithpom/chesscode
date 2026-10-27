---
name: chesscode-dev
description: Dev workflow for the ChessCode MCP server — run tests before rendering, how to visually QA rendered frames, and a flag/tool cheatsheet for main.py and the MCP tools.
---

# ChessCode Dev Workflow Skill

Use this skill when working on ChessCode's code (not when just creating a video — see the
`chess-video` skill for that creative workflow).

## Before calling any render tool

Run from the project root (`chess channel/`):

```
pytest -q
```

All tests must pass. This is the fast suite (`tests/` + `test_meme_inserter.py`) — cache
utils, config parsing, move-classification thresholds, job registry, content queue, opening/
channel stats caching, arrow-selection logic, bilingual/emotion text parsing, and the MCP
tool-layer contract (`tests/test_mcp_server.py`, which locks in the exact `main.py` command
line each `render_video`/`analyze_game` flag combination produces — no real render happens,
`subprocess.Popen` is mocked).

Also run the slow smoke test after touching dependencies, Stockfish, ffmpeg, or the TTS
backend config:

```
pytest -m slow
```

This runs `python main.py --test` (the real dependency/environment check) for real.

## Visual QA without a full render

A full render takes minutes. After changing `board_renderer.py`,
`stats_intro_renderer.py`, `avatar_generator.py`, or `arrow_analyzer.py`, instead inspect
existing frame PNGs directly (Read tool handles images):

```
output/<job_id>_pgn/frames/*.png       # board frames
output/<job_id>_pgn/tframes/*.png      # move-transition frames
```

or render one short 2-move test PGN through `main.py` if no recent frames exist. Look at:
board rendering + piece art, arrow overlays (green/red/yellow), move-list panel + highlighting,
brand/legend sidebar, stats intro card if `stats_intro=True`.

## MCP tool → main.py flag cheatsheet

Mirrors the dispatch in `mcp_server.py` (`call_tool`, `render_video` branch):

| `render_video` arg | `main.py` flag when set |
|---|---|
| `upload=True` | `--upload` |
| `hindi=True` | `--hindi` |
| `avatar=False` | `--no-avatar` (default `avatar=True` → no flag) |
| `stats_intro=False` | `--no-stats-intro` (default `stats_intro=True` → no flag) |
| `legend_name` | `--legend-name <name>` (+ `--legend-title`/`--legend-fact` if also passed) |

`analyze_game` and `generate_opening_video` always run full Stockfish analysis (no
`--no-claude`/`--provided-commentary`); only `render_video` uses pre-written commentary and
hardcodes `--quality ultrafast --depth 12` for turnaround speed.

## Fixed issues (2026-07-10 visual QA pass)

Both fixed — noted here so the reasoning isn't lost:

- **Opening moves falsely tagged "mistake"/"blunder".** Ruy Lopez book moves (`Nf3`, `Bb5`,
  `Ba4`, `Nf6`, `O-O`) rendered with a false "?" glyph because `--depth 12` (hardcoded in the
  MCP `render_video` path) produces eval noise large enough to cross
  `stockfish_analyzer._classify`'s `-20`/`-100` centipawn thresholds even on normal theory
  moves. Fixed via `_classify_move(delta, ply)` in `stockfish_analyzer.py`: the first
  `OPENING_BOOK_PLIES` (10) plies are forced to `"normal"` regardless of eval delta — real
  inaccuracies still get caught once the game leaves book. `tests/test_classification.py`
  covers the book-grace boundary.
- **Unbounded job dict.** `job_registry.py`'s bounded `JobRegistry` (max history, queue
  limits, archival) is now the actual job store in `mcp_server.py` (`_registry`), replacing
  the plain unbounded dict. `_launch_job` also now raises a clear `RuntimeError` if the queue
  is full instead of silently starting an untracked process. `job_monitor.py` needed no
  changes — `JobRegistry` grew `.values()`/`.items()`/`__len__`/`__contains__` so it's a
  drop-in dict-like replacement.
