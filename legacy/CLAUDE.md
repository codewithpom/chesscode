# CLAUDE.md — ChessCode

AI chess-commentary-video generator. Pipeline: **PGN → Stockfish analysis → LLM
commentary → TTS narration → animated board frames → intros/avatar/memes → ffmpeg
assembly → (optional) YouTube upload**. Supports bilingual (English + Hindi),
opening-theory explainers, and trap Shorts.

## Run

```bash
python main.py --test                       # dependency + API-key self-check (no render)
python main.py game.pgn                      # analyze a game (English)
python main.py game.pgn --hindi --upload     # bilingual + YouTube upload
python main.py --opening "Sicilian Najdorf"  # opening-theory video
python main.py --trap "Legal Trap" --shorts  # trap Shorts (1080x1920)
python main.py --dashboard                    # content-calendar dashboard, then exit

python mcp_server.py         # MCP stdio server (drives the pipeline from Claude Desktop)
python autonomous_runner.py  # scheduler daemon (uploads Mon+Thu 09:00 IST from the queue)
```

Common flags: `--quality <preset>`, `--codec <libx264|h264_qsv|h264_nvenc|h264_amf>`,
`--depth N`, `--theme <classic|blue|green|dark_mode>`, `--llm-backend`,
`--tts-backend`, `--no-avatar`, `--no-stats-intro`, `--no-arrows`,
`--provided-commentary-json PATH` (skip LLM, feed a per-move script). Full list:
`parse_args()` in [main.py](main.py).

## Pipeline (order in main.py `run_game_pipeline`)

1. [stockfish_analyzer.py](stockfish_analyzer.py) — parse PGN, run Stockfish
   (parallel workers), per-move eval/delta/classification. First
   `OPENING_BOOK_PLIES` plies get a classification pass so book moves aren't
   mislabeled.
2. [commentary_generator.py](commentary_generator.py) — LLM narration script
   (+ [bilingual.py](bilingual.py) for Hindi).
3. [tts_generator.py](tts_generator.py) — text → speech (pluggable TTS backend,
   per-segment parallel). Emotion tags via [emotion_tags.py](emotion_tags.py).
4. [board_renderer.py](board_renderer.py) — SVG board → PNG frames (python-chess +
   cairosvg), themes, move transitions, arrow overlays, rotating legend card.
   Arrow selection in [arrow_analyzer.py](arrow_analyzer.py).
   Formats in [scene_renderer.py](scene_renderer.py).
5. Intros: [stats_intro_renderer.py](stats_intro_renderer.py) (ratings / opening /
   channel-stats card), [opening_intro_renderer.py](opening_intro_renderer.py)
   (opening-theory card). Stats sources: [opening_stats.py](opening_stats.py),
   [channel_stats.py](channel_stats.py), [lichess_api.py](lichess_api.py).
6. [avatar_generator.py](avatar_generator.py) — optional talking-pawn overlay
   (SadTalker/Wav2Lip). [meme_inserter.py](meme_inserter.py) — captioned meme
   overlays on blunders.
7. [video_assembler.py](video_assembler.py) — ffmpeg mux: frames + audio + intro +
   avatar + memes → final MP4.
8. [thumbnail_leonardo.py](thumbnail_leonardo.py) — Leonardo AI (PIL fallback)
   thumbnail. [youtube_uploader.py](youtube_uploader.py) — OAuth2 + YouTube Data
   API v3.

Opening/trap videos go through [opening_video_generator.py](opening_video_generator.py)
+ [opening_fetcher.py](opening_fetcher.py).

## Backends (pluggable)

- **LLM** ([llm_backends/](llm_backends/)): `claude` (default) | `ollama`. Select via
  `LLM_BACKEND` env or `--llm-backend`. Factory in `llm_backends/__init__.py`.
- **TTS** ([tts_backends/](tts_backends/)): `kokoro` (default, local ONNX) |
  `elevenlabs` | `gtts`. Select via `TTS_BACKEND` or `--tts-backend`; `config.py`
  `active_tts_backend` falls back down the chain when a backend is unavailable.
- Retry/fallback wrapping in [backend_resilience.py](backend_resilience.py).

## Config

All settings in [config.py](config.py) (`ChessCodeConfig`, import `cfg`). Reads
`.env` automatically; see [.env.example](.env.example). Key vars: `ANTHROPIC_API_KEY`,
`ELEVENLABS_API_KEY`, `LEONARDO_API_KEY`, `LICHESS_TOKEN`, `LLM_BACKEND`,
`TTS_BACKEND`, `STOCKFISH_PATH`, `STOCKFISH_DEPTH` (18), `RESOLUTION`, `FPS`,
`VIDEO_CODEC`, `BOARD_THEME`, `YT_PRIVACY`, `AVATAR_ENABLED`, `ENABLE_MEMES`.
Content queue is SQLite via [content_calendar.py](content_calendar.py) (`DB_PATH`,
default `chesscode.db`).

## Tests

```bash
pytest -q            # fast suite (excludes @pytest.mark.slow) — the gate
pytest -m slow       # integration (real Stockfish/ffmpeg/TTS)
```

**Run `pytest -q` before rendering a video via the MCP server.** Config in
[pytest.ini](pytest.ini); shared fixtures in [tests/conftest.py](tests/conftest.py).

## External dependencies

- `pip install -r requirements.txt`. Also needs **ffmpeg** on PATH.
- **Stockfish**: vendored under `stockfish_bin/` (`STOCKFISH_PATH`). This is a
  third-party C++ engine — **do not edit it**.
- **Kokoro TTS**: `kokoro-v1.0.onnx` + `voices-v1.0.bin` in project root
  (download separately; git-ignored).
- **YouTube**: `client_secret.json` (Google Cloud OAuth) → `youtube_token.pickle`
  created on first auth. Both git-ignored.
- Hindi font: `assets/fonts/NotoSansDevanagari-Bold.ttf`.

## Don't touch / don't commit

`stockfish_bin/`, secrets (`.env`, `client_secret.json`, `youtube_token.pickle`),
model blobs (`*.onnx`, `voices-*.bin`), and generated `output/` — all git-ignored.

## Driving the MCP server

When calling the `chesscode` MCP tools (`render_video`, `analyze_game`,
`generate_opening_video`, etc.), first load the **`chesscode-mcp`** skill — it
has the exact current call signatures. In particular `render_video` takes
`intro` + `move_comments` (one string per ply) + `conclusion`, **not** a single
`commentary` string, and `coach_insights` populates the analysis sidebar.

## Skill observation logging

At the start of any task-oriented session — any interaction where you will
use tools and produce deliverables — invoke the task-observer skill before
beginning work. This ensures skill improvement opportunities are captured
throughout the session.

When loading any skill, check the observation log at
`skill-observations/log.md` for OPEN observations tagged to that skill.
Apply their insights to the current work, even if the skill file hasn't
been updated yet.
