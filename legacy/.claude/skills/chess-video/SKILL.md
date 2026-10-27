---
name: chess-video
description: Full workflow for creating a ChessCode chess commentary video — construct PGN with variations, write narration, call render_video MCP tool.
---

# Chess Video Creation Skill

Use this skill whenever the user wants to create a chess video (game analysis, opening theory, trap, etc.).

## Workflow

### Step 1 — Get the game

If user provides a PGN, use it directly.
If user describes a game in text (e.g. "Magnus vs Nepo, game 6 of WC 2021"), construct the PGN yourself from known games.
If user describes moves verbally (e.g. "e4 e5 Nf3 Nc6 Bb5"), build the PGN headers + moves.

Minimum required PGN headers:
```
[Event "?"]
[White "Player1"]
[Black "Player2"]
[Result "*"]
```

### Step 2 — Add variations to the PGN

Enrich the PGN with key alternate lines and move comments. Use standard PGN syntax:

```
[Event "Classical WC 2021 Game 6"]
[White "Magnus Carlsen"]
[Black "Ian Nepomniachtchi"]
[Result "1-0"]

1. d4 d5 2. c4 c6 {Slav Defense} 3. Nf3 Nf6
(3... dxc4 {Accepted - leads to sharp play} 4. e3 b5 5. a4)
4. Nc3 dxc4 5. a4 {Prevents b5} 5... Bf5 6. e3
```

Rules:
- `{comment}` — annotate a specific move inline
- `(moves...)` — alternate line; close with `)` before continuing main line
- Nested variations allowed: `(1... c5 (1... e5 {Open game}) 2. Nf3)`
- Keep variations to 3-5 key branches — don't over-annotate
- Only the **main line** renders on the board; variations appear in narration prose

### Step 3 — Write commentary narration

Write a single block of narration text. This is spoken as TTS audio over the video.

Guidelines:
- Cover the main line move by move, explaining plans and ideas
- Mention key variations in prose: "Instead of this, Black could have tried the Sicilian..."
- Keep it conversational and educational
- Typical length: 200–500 words for a full game, 100–200 for an opening/trap
- Do NOT number moves in narration — it sounds robotic when read aloud
- End with a summary of the key lesson

Example narration opening:
> "In this game from the 2021 World Chess Championship, Magnus Carlsen opens with d4, entering the Slav Defense. The key moment comes on move 36, where Nepo makes a critical mistake that costs him the game..."

### Step 4 — Write a video title

Format: `[Opening/Theme]: [Key idea or players] | Chess Analysis`
Examples:
- `Ruy Lopez: Magnus's Immortal Brilliance | Chess Analysis`
- `Sicilian Najdorf: The Sharpest Defense Explained | Chess Tutorial`
- `Queen's Gambit Trap: Win in 12 Moves | Chess Traps`

### Step 4.5 — Pick a chess legend to feature (optional)

The sidebar occasionally swaps its move list for a "chess legend" card (portrait + name + fact).
Pick one legend relevant to this video rather than letting it default every time:
- The actual player in the game, if they're a known legend
- Or one whose style matches the game (e.g. Tal for a sacrificial attack, Karpov for a positional squeeze)

Write `legend_title` (their defining title/era, e.g. `"World Champion 1960-1961"`) and
`legend_fact` (1-2 short, factually-accurate sentences, ~150 chars so it fits the wrapped card
without truncation).

This step is optional — omit `legend_name` to let the renderer fall back to its built-in
rotating default (Carlsen/Kasparov/Fischer/Tal/Karpov).

### Before Step 5 — run the test suite

Before calling `render_video`, `analyze_game`, or `generate_opening_video`, make sure
`pytest -q` passes in the project root (`chess channel/`). This is the regression net for the
MCP tool layer, config, caching, and pipeline logic — see the `chesscode-dev` skill for what
it covers and how to visually QA a render without waiting for a full ffmpeg assembly.

### Step 5 — Call render_video MCP tool

```
render_video(
    pgn="<your constructed PGN with variations>",
    commentary="<your narration text>",
    title="<your video title>",
    upload=False,   # set True to post to YouTube
    hindi=False,    # set True to also generate Hindi version
    avatar=True,    # set False to disable talking pawn overlay
    legend_name="Mikhail Tal",                              # optional, see Step 4.5
    legend_title="World Champion 1960-1961",                # optional, pass with legend_name
    legend_fact="The Magician from Riga, famous for brilliant piece sacrifices."  # optional
)
```

The tool returns the pipeline output. If it errors, report the last 500 chars of output to the user.

## Quick Reference

| Parameter | What to write |
|-----------|--------------|
| `pgn` | Full PGN with headers, variations `(...)`, comments `{...}` |
| `commentary` | Flowing prose narration, 200-500 words, no move numbers |
| `title` | YouTube-style title with opening name |
| `upload` | `True` only if user explicitly says "upload to YouTube" |
| `hindi` | `True` only if user asks for Hindi version |
| `avatar` | `False` only if user wants to disable the talking pawn overlay |
| `legend_name` | Omit to use the built-in rotating default; else name a legend relevant to the game (Step 4.5) |
| `legend_title` | Legend's subtitle, e.g. `"World Champion 1960-1961"`. Pass with `legend_name` |
| `legend_fact` | 1-2 sentence fact about the legend (~150 chars). Pass with `legend_name` |

## Notes

- No Stockfish needed — analysis is user/Claude-written
- TTS backend: Kokoro (local ONNX) — produces natural English voice
- Talking pawn avatar: SadTalker (local) lip-syncs pawn to audio; falls back to static if SadTalker not installed
- Avatar appears bottom-right corner (280×280px PiP overlay)
- Rendering takes 2–10 minutes depending on game length; avatar adds ~2-5 min if SadTalker installed
- Video saved to `output/` in the chess channel project directory
- Sidebar has two columns: a narrow move-history panel (players + moves, occasionally swapping
  to the legend card per Step 4.5) and a static decorative brand panel on the outer edge
- The MCP `render_video` path runs Stockfish at a shallow `--depth 12` for speed; opening-book
  moves are given a classification grace period so they're never mistagged "mistake"/"blunder"
  on screen (fixed 2026-07-10 — see the `chesscode-dev` skill for details).
