---
name: chesscode-mcp
description: Correct call signatures for the ChessCode MCP server (chesscode) — how to call render_video, analyze_game, generate_opening_video and the other tools with the exact required fields so calls don't fail or render an empty sidebar.
---

# ChessCode MCP — Correct Tool Usage

Use this skill whenever you drive the ChessCode pipeline through the `chesscode`
MCP server. It documents the **exact** current tool signatures. Get these wrong
and the call fails schema validation, or renders a video with an empty coach
sidebar.

The MCP tool names are prefixed `mcp__chesscode__` in the tool list.

## Before any render — run the tests

Run `pytest -q` in the project root before `render_video`, `analyze_game`, or
`generate_opening_video`. It's the regression net for the MCP layer. Renders are
slow (2–10 min); don't launch one on a broken tree.

## Two ways to make a game video

| You have… | Use | Who writes the analysis |
|-----------|-----|-------------------------|
| A PGN + your own move-by-move commentary | `render_video` | You (Claude) |
| A raw PGN, want Stockfish to do it | `analyze_game` | Stockfish + LLM, automatic |
| Just an opening name | `generate_opening_video` | Automatic |

## render_video — the one that trips people up

**Required:** `pgn`, `intro`, `move_comments`, `conclusion`, `title`.

There is **no `commentary` string**. Narration is split into three parts:

- `intro` — one sentence, spoken over the start position.
- `move_comments` — **array of strings, one per main-line ply, in order. Length
  MUST equal the number of plies in the PGN main line.** Each is narrated and
  captioned on that move's frame. A length mismatch misaligns every caption.
- `conclusion` — one sentence over the final position.

```
render_video(
    pgn="[Event \"?\"]\n[White \"Carlsen\"]\n[Black \"Nakamura\"]\n[Result \"*\"]\n\n1. e4 e5 2. Nf3 Nc6 3. Bb5",
    intro="Magnus opens with the Ruy Lopez, chess's oldest respected weapon.",
    move_comments=[
        "e4 — grabbing the center immediately.",
        "e5 — Nakamura meets him head on.",
        "Nf3 — developing and hitting e5.",
        "Nc6 — defending the pawn.",
        "Bb5 — the Spanish bishop pins the knight."
    ],   # exactly 5 entries for these 5 plies
    conclusion="A classic Ruy Lopez setup, rich with strategic ideas.",
    title="Ruy Lopez Explained | Chess Analysis"
)
```

### Populate the sidebar with `coach_insights`

The right sidebar "Candidate Move Breakdown / Coach's Tactical Insights" panel is
driven by the optional `coach_insights` array — one object per ply:

```
coach_insights=[
    {
        "top_engine_moves": [
            {"san": "Bb5", "score_cp": 50, "rank": 1, "label": "best"},
            {"san": "d4",  "score_cp": 27, "rank": 2, "label": ""},
            {"san": "Nc3", "score_cp": 23, "rank": 3, "label": ""}
        ],
        "insights": ["<b>Bb5</b> pins the knight.", "Central tension builds.", "White keeps the edge."]
    },
    ...  # one object per ply, same length as move_comments
]
```

`insights` = up to 3 short strings, optional `<b>…</b>` bold, ≤12 words each.
`score_cp` is centipawns from White's side. If you omit `coach_insights`, the
renderer now auto-fills the panel from Stockfish's own top moves — so the sidebar
is no longer blank, but LLM-written insights read better.

### Optional render_video params

| Param | Use |
|-------|-----|
| `upload` | `True` only if the user explicitly says upload to YouTube |
| `publish_at` | ISO 8601 UTC to schedule the publish (requires `upload=True`) |
| `hindi` | `True` to also make a Hindi version — then also pass `hindi_intro`, `hindi_conclusion` (Devanagari) |
| `avatar` | `False` to drop the talking-pawn overlay |
| `theme` | `classic` (wood) · `cyberpunk` (neon) · `retro` (pixel) |
| `legend_name` / `legend_title` / `legend_fact` | Feature a chess legend card; omit for the rotating default |

## analyze_game — let Stockfish do it

Required: `pgn`. Optional: `title`. Runs async, returns a `job_id`. No commentary
needed — Stockfish evaluates and the LLM backend writes narration + coach panel.

```
analyze_game(pgn="<raw pgn>", title="My Game Analysis")
```

## generate_opening_video

Required: `opening_name`. Optional: `variation`, `pgn_moves`, `shorts` (vertical
1080×1920), `legend_name` / `legend_title` / `legend_fact`.

```
generate_opening_video(opening_name="Sicilian Najdorf", shorts=False)
```

## Job control

- `get_job_status(job_id, tail=50)` — status + last N log lines of an async job.
- `cancel_job(job_id)` — terminate + clean up. Safe on finished/unknown ids.

Poll `get_job_status` after `analyze_game` / `generate_opening_video` / a
backgrounded `render_video` rather than assuming it's done.

## Queue (autonomous scheduler)

- `add_to_queue(content_type, content_id, title, priority=5)` — `content_type` is
  `game` | `opening` | `trap`; `content_id` is a PGN path (games) or a name
  (openings/traps).
- `get_queue()` — current queue + status.
- `run_next()` — render the next queued item now (synchronous, slow).

## Utility tools

- `fetch_lichess(path, host="lichess.org", params={})` — proxy a Lichess API call,
  e.g. `path="/api/opening/explorer"`.
- `get_api_key_status()` — which credentials are configured (never shows values).
  Call this first if a render fails on a missing key.
- `generate_thumbnail(title, prompt=…, size="1280x720", style_preset=…)` — needs
  `OPENAI_API_KEY`.
- `pull_stats(video_id=…, channel_id=…)` — live YouTube stats after publishing.
  Omit `channel_id` to use the configured one.

## Fast local iteration (not MCP)

To preview render changes without waiting on slow Kokoro TTS, run the CLI with
`--fast-test`: forces gTTS + shallow Stockfish depth and skips the avatar +
stats-intro. Example:
`python main.py game.pgn --fast-test --no-claude --output output/_smoke`.
