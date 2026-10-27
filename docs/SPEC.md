# ChessCode v2: Remotion Video Engine Spec

Oct 27, 2026 · @Padmashree Jha

## 0. How Claude Code should use this spec

Claude Code: this document is the source of truth for the build. Read it fully once, then turn it into an implementation plan with the Superpowers `writing-plans` skill, and execute that plan with subagents routed by cost as described below. Where this spec and your own judgment disagree, raise it as a question before building, not after.

### Reading order

1. Sections 1, 2 and 3 (goals, architecture, the JSON contract). Nothing else makes sense without them.
2. Section 13 (timeline). The Nov 15 deadline overrides every nice-to-have in this document.
3. Sections 4 to 11 as each workstream starts.
4. Sections 12 and 14 (QA gates, risks) before any batch render or upload.

### Skills and plugins to install first

CLI syntax changes often. Run `--help` or check each repo's README before trusting a command copied from here.

| Tool | Why | Install |
| --- | --- | --- |
| [Superpowers](https://github.com/obra/superpowers) | Planning, subagent execution, TDD, debugging, verification discipline | `/plugin install superpowers@claude-plugins-official` (or `/plugin marketplace add obra/superpowers-marketplace` then `/plugin install superpowers@superpowers-marketplace`) |
| [Remotion agent skills](https://github.com/remotion-dev/skills) | Correct Remotion patterns: rendering, captions, media, Studio | `npx skills add remotion-dev/skills` |
| [Impeccable](https://github.com/pbakaus/impeccable) | Design quality: anti-slop detection, critique, typesetting, layout, animation polish | `npx impeccable install`, then `/impeccable init` |
| frontend-design (Anthropic) | Distinctive visual direction, avoids templated defaults | `/plugin install frontend-design@claude-plugins-official` |
| [LottieFiles motion-design-skill](https://github.com/LottieFiles/motion-design-skill) | Plans timing, easing and choreography before code | `npx skills add LottieFiles/motion-design-skill` |

Superpowers skills to use, by name: `writing-plans`, `executing-plans`, `subagent-driven-development`, `dispatching-parallel-agents`, `test-driven-development`, `systematic-debugging`, `requesting-code-review`, `receiving-code-review`, `verification-before-completion`, `using-git-worktrees`, `finishing-a-development-branch`. Skip `brainstorming`: the brainstorming already happened and produced this spec.

Impeccable commands to use (they run as `/impeccable <command> <target>`): `shape` and `craft` when first building each template, `critique` and `audit` on every rendered still, `typeset`, `layout` and `animate` for focused passes, `polish` before the template is frozen. Run `npx impeccable detect` on the Remotion `src/` folder in CI.

### Model routing: expensive models for judgment, cheap models for volume

Create these subagents in `.claude/agents/`. Each file needs `name`, `description` and a `model` line (`haiku`, `sonnet`, `opus`, or `inherit`). Keep `tools` minimal per agent.

| Agent file | Model | Does | Never does |
| --- | --- | --- | --- |
| main session | opus | Plans, architecture, design direction, reviewing subagent output, final decisions | Bulk edits |
| `remotion-builder.md` | sonnet | Implements Remotion components and compositions from the plan | Design decisions not in the plan |
| `python-builder.md` | sonnet | Implements pipeline modules with TDD | Changes the JSON schema |
| `design-critic.md` | opus | Renders stills, runs Impeccable `critique`/`audit`, writes a fix list | Edits code itself |
| `spec-validator.md` | haiku | Validates specs, checks pacing rules, compares upload log to plan | Anything creative |
| `line-checker.md` | haiku | Checks every mascot line against the joke rules (section 8); flags violations | Writing new jokes |
| `qa-frames.md` | haiku | Looks at sampled frames per video (section 12) and reports defects as JSON | Fixing defects |
| `docs-scout.md` | haiku | Looks up library docs and API references on demand | Writing code |

Rules: parallelize with `dispatching-parallel-agents` only when tasks touch different files. Use `using-git-worktrees` for anything that runs longer than one session. Every subagent ends with `verification-before-completion`: a claim of done needs a passing command or a rendered still as evidence.

### Independent auditors (other vendors' agents)

Outside agents review the work read-only, so the code is never graded only by the model that wrote it. They write reports into `audits/`; Claude Code triages each finding as fix, defer or reject with a one-line reason in `audits/TRIAGE.md`.

- OpenAI Codex CLI: `codex exec -m gpt-6.1-sol -s read-only -o audits/<gate>-codex.md "<audit prompt>"`. Use `gpt-6-astra` for the architecture audit. `codex review --base main` for branch reviews. `--full-auto` is no longer supported; never give an auditor `danger-full-access`.
- Google Antigravity CLI: `agy -p "<audit prompt>" --output-format json > audits/<gate>-agy.json`. Gemini CLI (`gemini -p`) is the fallback if `agy` is unavailable on the account.
- Claude Code may also spawn these auditors itself through Bash when a gate is reached; the owner may also run them by hand.

Audit gates (each gate blocks the next milestone until triaged):

1. Gate A, contract: schema, beat detection, timing math (after milestone M2).
2. Gate B, look: the Studio template stills and a 60-second render, judged against section 6 (after M5).
3. Gate C, pre-batch: one complete EN and one complete HI video, end to end (before the batch run).
4. Gate D, pre-upload: the upload script and the first 5 scheduled uploads (before bulk upload).

### Human checkpoints (the owner must answer; do not guess)

- Mascot concept choice (section 7).
- TTS voice choice for EN and HI after hearing samples (section 4).
- Approval of the Studio template from 6 stills plus one 60-second clip.
- Sign-off on the first full EN and HI videos before the batch run.
- Line bank review (section 8).

## 1. Goals, non-goals and success criteria

The one outcome that matters: by the end of Nov 15, 2026, ChessCode has 13 weeks of videos (Nov 16, 2026 to Feb 15, 2027) uploaded to YouTube as private with a publish date, so the channel publishes on schedule with zero human input while the owner is offline.

### Goals

1. Replace the Pillow frame renderer with a Remotion renderer that looks broadcast-grade, not template-generated.
2. Keep the existing Python pipeline as the brain: game sourcing, Stockfish analysis, commentary, TTS. Python emits one `video_spec.json` per video; Remotion only draws.
3. Ship one finished template (Studio, 16:9) and the Shorts template (9:16) before the backlog run. Editorial and Arena are post-return work.
4. Ship one original mascot with a pose library and a data-driven reaction system that makes videos funny without hand-written jokes per video.
5. Batch-render the whole backlog on GitHub Actions, then upload everything as scheduled videos via the YouTube Data API.

### Non-goals for this phase

- No live or news content (tournament round recaps). Everything must still be relevant up to three months after rendering.
- No server that runs while the owner is offline. All automation finishes before Nov 15; YouTube's own scheduler does the publishing.
- No comment replies, community posts or analytics loops during the offline period.
- No third template until the first two are proven on real uploads.

### Backlog sizing

13 weeks offline. Two tiers, so the floor is always protected:

| Tier | Long-form per week | Shorts per week | Long-form total | Shorts total | Uploads total |
| --- | --- | --- | --- | --- | --- |
| Floor (must ship) | 1 game × EN + HI = 2 | 3 | 26 | 39 | 65 |
| Target | 2 games × EN + HI = 4 | 4 | 52 | 52 | 104 |

Rendering and review, not uploading, are the bottleneck. The current YouTube API quota allows 100 uploads a day (section 10), so all 104 uploads fit in two days. The real limits are GitHub Actions render time and the human checks in section 12. Batches therefore upload as soon as they pass automated QA, and the owner reviews them in YouTube Studio while they sit scheduled. The floor tier is rendered and uploaded first; target-tier videos are added on top as time allows.

### Success criteria (all must be true on Nov 15)

- [ ] Every floor-tier video shows as Scheduled in YouTube Studio with the correct date, title, thumbnail, playlist and language.
- [ ] No two videos share a game, and no scheduled date has two long-form uploads in the same language.
- [ ] Every video passed the QA gates in section 12.
- [ ] The upload log (CSV in the repo) matches YouTube Studio one to one.
- [ ] The old Pillow pipeline still runs, as the fallback.

## 2. System architecture

Each video is produced by one self-contained GitHub Actions job: Python builds a spec, Remotion renders it, QA checks it, and the uploader schedules it on YouTube. After Nov 15 only YouTube's own scheduler is running.

&#91;embedded content: system architecture · one job per video, then YouTube's scheduler\]

Arrows run left to right on the top row and right to left on the bottom; a video that fails QA never reaches the upload box.

### Design principles

1. One contract. Python and Remotion share only `video_spec.json` (section 3). Either side can be rewritten without touching the other.
2. Deterministic rendering. Same spec in, same frames out. All randomness is seeded; no network calls during render.
3. Idempotent everything. Every stage can be re-run; the uploader can never create a duplicate.
4. Fail closed. A failed check stops that video, never the batch, and never uploads.
5. Nothing runs while the owner is away. No cron jobs, servers or tokens that need refreshing after Nov 15.
6. The old pipeline stays as the fallback until Gate D passes.

### Repository layout (monorepo)

```
chesscode/
  pipeline/chesscode/   Python package: select, fetch, analyze, classify, beats,
                        script, voice, timeline, metadata, emit, upload, qa
  remotion/             Remotion project (section 5)
  spec/                 video_spec.schema.json (exported from Zod)
  config/               beats.yaml, classify.yaml, models.yaml, calendar.yaml, qa.yaml
  content/              games.yaml, lines/en.yaml, lines/hi.yaml
  data/                 engine_cache.sqlite, line_history.sqlite, upload_log.csv
  build/                spec folders and renders (git-ignored)
  audits/               auditor reports + TRIAGE.md
  legacy/               the current Pillow + MoviePy pipeline, untouched
  .claude/agents/       subagent definitions (section 0)
  .github/workflows/    ci.yml, batch.yml, collect.yml, audit.yml
```

### Command-line interface

- `python -m chesscode run --video <id> [--stage <name>] [--until <name>]`
- `python -m chesscode batch plan --tier floor|target` writes the list of video ids for `batch.yml`
- `python -m chesscode upload --video <id> [--repair]`
- `python -m chesscode auth check`
- `python -m chesscode qa --video <id>`
- `python -m chesscode ledger verify` compares `upload_log.csv` with the channel's scheduled videos

## 3. Video spec JSON (the contract)

One `video_spec.json` per video is the only interface between Python and Remotion. Python writes it; Remotion reads it as input props and never calls an API, an engine or a TTS service. If a render looks wrong, the spec is either wrong (Python bug) or drawn wrong (Remotion bug), never both at once.

### Rules

- All times are integer milliseconds from the start of the video. Remotion converts to frames with `Math.round(ms * fps / 1000)` in exactly one helper (`msToFrame`).
- All asset paths are relative to the spec file's folder (`audio/en_0012.mp3`), so a spec folder can be zipped, moved to a runner and rendered anywhere.
- The schema is defined once in TypeScript with Zod (`remotion/src/spec/schema.ts`) and exported as JSON Schema (`spec/video_spec.schema.json`). Python validates every spec against that JSON Schema with `jsonschema` before writing it. A spec that fails validation never reaches a render job.
- `spec_version` is a semver string. Remotion refuses a spec whose major version it does not know.
- Every field below is required unless marked optional. No silent defaults on the Python side: if a value is missing, the pipeline stops for that video and logs why.

### Example (abridged)

```json
{
  "spec_version": "1.0.0",
  "video_id": "cc-2026-0042-en",
  "pair_id": "cc-2026-0042",
  "language": "en",
  "template": "studio",
  "format": { "width": 1920, "height": 1080, "fps": 30 },
  "duration_ms": 612400,
  "game": {
    "source": "lichess",
    "source_id": "abcd1234",
    "white": { "name": "Player A", "rating": 2810, "title": "GM", "country": "NO" },
    "black": { "name": "Player B", "rating": 2783, "title": "GM", "country": "IN" },
    "event": "Example Event", "date": "2024-05-30", "result": "1-0",
    "eco": "B90", "opening": "Sicilian Defense: Najdorf Variation",
    "pgn": "[Event ...] 1. e4 c5 ..."
  },
  "plies": [
    {
      "ply": 1, "san": "e4", "uci": "e2e4",
      "fen_after": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
      "eval": { "cp": 30, "mate": null }, "best_uci": "e2e4",
      "class": "book", "clock_ms": 5400000,
      "show_at_ms": 41200, "arrows": [], "highlights": []
    }
  ],
  "narration": [
    {
      "segment_id": "seg-007", "kind": "ply", "ply": 23,
      "text": "And there it is. The knight walks straight into a fork.",
      "audio": "audio/en_seg-007.mp3", "start_ms": 233400, "duration_ms": 3900,
      "words": [ { "w": "And", "start_ms": 233400, "end_ms": 233560 } ]
    }
  ],
  "beats": [
    {
      "beat_id": "b-05", "type": "blunder", "ply": 23, "at_ms": 233400,
      "intensity": 3, "mascot": { "pose": "facepalm", "line": "Bro sold the knight for nothing." },
      "fx": ["board_shake", "replay_move"], "sfx": "oof_01"
    }
  ],
  "chapters": [ { "title": "The opening", "start_ms": 0 } ],
  "music": { "track": "music/bed_calm_02.mp3", "volume": 0.12, "duck_under_voice": 0.06 },
  "youtube": {
    "title": "...", "description": "...", "tags": ["chess"],
    "playlist": "Legendary Games", "publish_at": "2026-11-18T13:30:00Z",
    "default_language": "en", "made_for_kids": false,
    "contains_synthetic_media": false, "thumbnail": "thumb.png"
  }
}
```

### Field reference

| Field | Type | Meaning and rules |
| --- | --- | --- |
| `video_id` | string | Unique, `cc-<year>-<4-digit game no>-<lang>`. Also the output file name and the upload log key. |
| `pair_id` | string | Shared by the EN and HI versions of the same game, so both are never scheduled on the same day. |
| `language` | `en` or `hi` | Drives fonts, caption line breaking and the mascot line language. |
| `template` | `studio`, `shorts`, later `editorial`, `arena` | Selects the Remotion composition. `shorts` requires `format` 1080 × 1920 and `duration_ms` ≤ 175000. |
| `duration_ms` | int | Computed by Python as end of last audio + outro length. Remotion uses it in `calculateMetadata`. |
| `plies[].eval` | object | White-perspective centipawns, or `mate` as signed moves to mate. Exactly one is non-null. |
| `plies[].class` | enum | `book`, `best`, `excellent`, `good`, `inaccuracy`, `mistake`, `blunder`, `brilliant`, `missed_win`. Computed in Python (section 4). |
| `plies[].show_at_ms` | int | When the move is played on screen. Python aligns it to the start of that move's narration, never mid-word. |
| `plies[].arrows` | list | \`{from, to, color: best |
| `narration[]` | list | Ordered, non-overlapping. `words[]` comes from TTS word timestamps and drives captions. |
| `beats[]` | list | Every comedic or dramatic moment (section 8). Remotion maps `type` + `intensity` to mascot pose, effects and sound. |
| `youtube` | object | Everything the uploader needs. `publish_at` is UTC ISO 8601. |

### Folder layout per video

```
build/specs/cc-2026-0042-en/
  video_spec.json
  audio/en_seg-000.mp3 ... en_seg-061.mp3
  thumb.png        (rendered by Remotion's Thumbnail composition)
  out.mp4          (written by the render job)
  qa.json          (written by QA, section 12)
```

## 4. Python pipeline (the brain)

Keep the existing 17-module pipeline and refactor it so its final output is a validated spec folder instead of rendered frames. The Pillow renderer, MoviePy assembly and old uploader stay in the repo untouched as the fallback path until Gate D passes.

### Stages

1. `select` — reads `content/games.yaml` (the curated backlog list) and picks the next unrendered game.
2. `fetch` — gets PGN from Lichess (`GET /game/export/{id}` or broadcast `.pgn` endpoints) or a local PGN file for classic games. Caches raw PGN in `data/pgn/`.
3. `analyze` — Stockfish via `python-chess`, fixed depth (default 20) with MultiPV 2, cached per FEN in `data/engine_cache.sqlite` so re-runs are free.
4. `classify` — move classes (section 3) from win-probability loss, using the same logistic win% formula Lichess uses; thresholds in `config/classify.yaml`.
5. `beats` — beat detection and pacing (section 8).
6. `script` — commentary in EN and HI, written separately, not translated (below).
7. `voice` — TTS per narration segment, word timings, loudness normalization.
8. `timeline` — lays segments end to end, sets `show_at_ms` per ply, inserts reaction gaps, computes `duration_ms`.
9. `metadata` — YouTube title, description with chapters, tags, playlist, `publish_at` from the calendar (section 11).
10. `emit` — writes `video_spec.json`, validates it against the JSON Schema, writes the spec folder.

Each stage reads and writes files in the spec folder, so any stage can be re-run alone (`python -m chesscode run --stage voice --video cc-2026-0042-en`). Each stage is idempotent and skips work whose inputs have not changed (hash of inputs stored in `build/specs/<id>/.stage_hashes.json`).

### Game sourcing rules

- Evergreen only: famous classic games, legendary players, opening ideas, "best blunders" style compilations from older games. Nothing that depends on a tournament still running.
- Game moves are facts; all commentary, titles and visuals are original. Note sources in each video description ("Game source: Lichess").
- Lichess's database exports are CC0. API-exported broadcast games are used for move data only.
- Respect Lichess rate limits: one request at a time, back off at least 60 s after any HTTP 429.
- `games.yaml` holds at least 70 games before the batch week (52 target plus spares for games that fail QA).

### Script generation (Claude API)

- Model: Claude Sonnet for scripts; Claude Haiku for the cheap checks (line rules, SAN validation summaries). Model names live in `config/models.yaml`, not in code.
- Input to the model: the PGN, the per-ply eval and class table, detected beats, player and event facts, the joke rules (section 8), and the series format (section 11). Output: strict JSON (segments, mascot lines per beat, title options, description) validated with a schema; retry up to 2 times on invalid JSON.
- Hindi is written natively from the same facts, in the conversational register described in section 8. Never machine-translate the English script.
- Hallucination guard: every SAN move mentioned in the script must appear in the game or in the engine's best line for that ply. A regex extracts SAN tokens; any unknown move fails the segment, which is regenerated.
- Every script must contain specific, game-only analysis (the key plan, the turning point, the losing mistake). This is also the main defense against YouTube's inauthentic content policy (section 10).
- Target length: about 150 spoken words per minute in EN and about 140 in HI; long-form 8 to 12 minutes; Shorts 35 to 60 s built from one beat.

### TTS (voice)

Word-level timings are mandatory, because captions and move timing depend on them. Choose the provider by a bake-off in week 1: render the same 60-second EN and HI script with each, and the owner picks by ear.

| Provider | Word timing | Hindi | Price (as checked Oct 2026) | Notes |
| --- | --- | --- | --- | --- |
| [ElevenLabs](https://elevenlabs.io/pricing/api) Multilingual v2 / v3 | Character timestamps ([convert-with-timestamps](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)); group into words on spaces | Supported, test Devanagari timing quality | $0.08 per 1K characters (Flash $0.04) | Most natural; request limit 5K chars (v3), 10K (v2) |
| [Azure Speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis) | `WordBoundary` events with per-word offsets | Confirm hi-IN voices via the voice list API | Check current pricing | Strongest verified word timing |
| [Sarvam Bulbul](https://docs.sarvam.ai/api/getting-started/pricing.md) | Not confirmed; use forced alignment | Built for Indian languages | v3 ₹30 per 10K chars; v4 Flash ₹10 | Commercial use needs Sarvam's commercial rights |
| Google Chirp 3 HD | Treat as none | hi-IN since Mar 2025 | Check | `<mark>` not supported on Chirp 3 HD |

- Fallback for any provider without usable timings: forced alignment with WhisperX on the generated audio.
- Budget sanity check: a 10-minute script is about 9,000 characters, so roughly $0.72 per long video at $0.08 per 1K; the whole target backlog is well under $100 of TTS.
- Normalize every segment with ffmpeg `loudnorm` to -14 LUFS integrated, -1 dBTP; store as 48 kHz MP3 (Remotion and Lambda both handle MP3 fastest).
- Cache audio by hash of (provider, voice, text), so re-renders never re-bill.

### Tests (TDD, `pytest`)

- Classification and beat detection: golden tests on 10 known games with hand-checked expected beats.
- Timeline: no overlapping narration; every `show_at_ms` falls at or after its segment start; `duration_ms` equals last audio end plus outro.
- Emit: every spec in `tests/fixtures/` validates; a broken spec fails with a readable error.
- SAN guard: a script mentioning an illegal move is rejected.

## 5. Remotion project (the renderer)

Remotion 4.x (4.0.539 on npm as of Oct 27, 2026), with every `remotion` and `@remotion/*` package pinned to the same exact version. Do not upgrade to 5.0 during this project; its docs say the license and some APIs change. The free Remotion license covers individuals and companies of up to 3 people, including commercial use, so this channel qualifies ([license](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)).

### Setup

- `npx create-video@latest` (blank TypeScript template) into `remotion/`.
- Add packages: `@remotion/captions`, `@remotion/transitions`, `@remotion/shapes`, `@remotion/noise`, `@remotion/google-fonts` (dev-time only, see Fonts), `zod`, `chess.js`.
- `npx remotion browser ensure` in CI to pre-download Chrome Headless Shell.
- Read the Remotion agent skills (`remotion-best-practices` first) before writing any component.

### Folder structure

```
remotion/src/
  Root.tsx                 registers all compositions
  spec/schema.ts           Zod schema = the contract (section 3)
  spec/time.ts             msToFrame, frameToMs, the only timing helpers
  compositions/
    StudioVideo.tsx        16:9 long-form
    ShortsVideo.tsx        9:16
    Thumbnail.tsx          1280x720 still
    MascotSheet.tsx        every pose in a grid, for review
    TemplateGallery.tsx    one still per scene type, for design review
  scenes/                  ColdOpen, TitleCard, PlayerIntro, Playback, KeyMoment, Verdict, Outro
  board/                   Board, Square, Piece, Arrows, Highlights, positions.ts
  ui/                      EvalBar, MoveList, PlayerCard, Clock, ChapterCard, Captions, Lower third
  mascot/                  rig, poses, reactions (section 7)
  fx/                      shake, flash, stamp, glint, trail
  theme/                   tokens.ts + one file per template
  audio/                   NarrationTrack, MusicBed, Sfx
public/                    fonts, pieces, sfx, music (all licensed, see CREDITS.md)
```

### Data flow inside Remotion

- `calculateMetadata` reads the spec props and returns `durationInFrames = msToFrame(duration_ms)`, `width`, `height` and `fps` from `format`. It never measures audio; Python already did.
- `positions.ts` replays the PGN once with chess.js and memoizes the FEN and piece list for each ply. Components look up state by frame; nothing re-parses PGN per frame.
- Determinism: no `Math.random`, no `Date.now`, no network calls during render. Use Remotion's `random(seed)` for idle mascot motion. The same spec must produce the same frames every time.

### Board

- Custom SVG board (64 rects, coordinates, highlight layers, arrows). Do not use chessground (GPL-3.0) and do not use react-chessboard (interactive DOM, not needed).
- Pieces: an SVG set with a commercial-friendly license, such as rhosgfx (CC0) or an MIT set from the Lichess repo's license list ([COPYING.md](https://raw.githubusercontent.com/lichess-org/lila/master/COPYING.md)). Avoid cburnett and the other GPL/AGPL sets and every CC BY-NC-SA set. Record each asset's license in `public/CREDITS.md`.
- Move animation: the piece slides from source to target over 280 ms using one shared easing curve; captures fade the captured piece over the last 120 ms; castling moves king and rook together; promotion swaps the piece at the end with a short scale pop; en passant removes the correct pawn.
- Highlights: last move (soft), check (red glow on the king square), best-move arrow and threat arrow (max 2 arrows on screen).
- Board orientation is set per video in the spec (default: winner at the bottom).

### Eval bar

- Map eval to a win probability with the same logistic curve Python uses, then to bar height. Never map raw centipawns linearly.
- Animate changes with a spring (no overshoot past the clamp). Mate shows `M3`-style text and fills the bar.
- On a `blunder` beat, the bar whips to its new value, then settles.

### Captions

- Build caption pages with `createTikTokStyleCaptions` from `@remotion/captions`, fed from `narration[].words`. Each token's text must start with a space, because spaces are the delimiters.
- Long-form: two lines max, lower third, the current word highlighted. Shorts: one to three words at a time, large, centered above the board.
- Hindi: break on spaces only, never inside a word; test Devanagari conjuncts and matras render correctly at every caption size.

### Audio

- One `<Audio>` per narration segment inside a `<Sequence>` starting at its `start_ms`.
- Music bed at the spec's volume, ducked to `duck_under_voice` whenever narration is active (volume callback per frame, 200 ms ramps).
- Sound effects only on beats; never louder than the voice.

### Fonts

- Self-host fonts in `public/fonts/` and load them with `FontFace` + `staticFile` inside `delayRender`/`continueRender`, so CI renders never depend on Google Fonts being reachable.
- If `@remotion/google-fonts` is used during development, always pass explicit `weights` and `subsets` (for example `subsets: ['devanagari', 'latin']`). Calling `loadFont()` with no arguments loads every weight and causes `delayRender` timeouts.
- Devanagari candidates: Noto Sans Devanagari, Mukta, Hind (all on Google Fonts with a `devanagari` subset). Pair with the Latin face chosen in section 6.

### Scenes: long-form (Studio)

| Scene | Length | Content |
| --- | --- | --- |
| ColdOpen | 6 to 10 s | The game's biggest beat, played first, mascot reaction, one-line hook. No logo intro. |
| TitleCard | 2.5 s | Title, players, year. Fast, quiet. |
| PlayerIntro | 5 to 8 s | Two player cards, ratings, one fact each. |
| Playback | Most of the video | Board, eval bar, move list, captions, chapter cards between phases. |
| KeyMoment | 15 to 40 s each | Slower replay of a beat with arrows, alternative line, mascot. |
| Verdict | 10 to 15 s | Result, the turning point, accuracy per side. |
| Outro | 20 s | Mascot sign-off, empty space reserved for YouTube end-screen elements. |

### Scenes: Shorts

Hook text in the first second, one beat only, board filling the upper 60% of the frame, captions above the board, mascot below, maximum 59 s by default (YouTube allows up to 3 minutes). The last frame matches the first frame closely, so the loop feels seamless.

### Rendering commands

```bash
npx remotion render StudioVideo build/specs/<id>/out.mp4 \
  --props=build/specs/<id>/video_spec.json \
  --codec=h264 --crf=18 --x264-preset=veryfast --concurrency=100%

npx remotion still Thumbnail build/specs/<id>/thumb.png \
  --props=build/specs/<id>/video_spec.json
```

Run `npx remotion benchmark` once on the CI runner to pick `--concurrency`. There is no official 1080p30 benchmark for a 4-vCPU machine, so measure: render one real 10-minute video in week 1 and use that number for the capacity plan in section 9.

## 6. Design system and templates

One design system, four templates. Every template reads the same tokens file and differs only in values, so the channel looks like one brand and nothing looks assembled from parts. Studio and Shorts ship before Nov 15; Editorial and Arena are specified here so the token structure supports them, but are built after the owner returns.

### Starting point (owner may override at the Studio checkpoint)

These are deliberate defaults, not final taste. Claude Code should run Impeccable `shape` and the frontend-design skill to challenge them, then show the owner the result as stills.

- Type: IBM Plex family, because it has Latin, Mono and Devanagari cuts that were designed together, so English and Hindi videos look like the same brand. Plex Sans for UI, Plex Sans Condensed for titles, Plex Mono for moves and evals (tabular figures), Plex Sans Devanagari for Hindi. All SIL Open Font License; self-hosted.
- Studio palette (dark): background `#0F1115`, surface `#171A21`, hairline `#262A33`, text `#ECEEF2`, muted text `#9097A3`. Board: light `#E8E2D4`, dark `#6E7F86`. Semantic colors used only for move quality: best `#3DD68C`, brilliant `#F2A93B`, mistake `#F5A524`, blunder `#E5484D`. One accent per scene, never all at once.
- The existing ChessCode colors (`#161B26` / `#1E2533`) may be kept instead if the owner wants continuity with older uploads.

### Layout (Studio, 1920 × 1080)

- 8 px spacing grid; outer margins 96 px; safe area respected for YouTube's player UI.
- Board 800 × 800 at the left, vertically centered; eval bar 24 px wide, 16 px left of the board.
- Right column (from x = 1000): player cards at the top, move list in the middle (current move centered, 9 visible rows), mascot anchored bottom-right.
- Captions: lower area under the right column, never over the board.
- Chapter cards and key-moment labels appear top-left of the right column, not centered over everything.

### Layout (Shorts, 1080 × 1920)

- Board 960 × 960 centered in the upper 60% of the frame; eval bar as a thin horizontal bar above the board.
- Captions above the board; mascot below the board; keep the bottom 340 px and the right 120 px free of anything important (YouTube Shorts UI covers them).

### Motion rules

- One enter easing for the whole channel (`cubic-bezier(0.22, 1, 0.36, 1)`), one exit easing, one spring config for UI (no visible overshoot). Defined once in `theme/motion.ts`.
- Piece moves 280 ms; UI enters 240 to 360 ms; nothing on screen moves without a reason (a move, a beat, a scene change).
- At most one element enters at a time; stagger 60 ms if two must.
- Scene transitions are hard cuts or a short slide. No spinning, zoom-punches, glitch or whoosh-on-everything.
- Plan timing and choreography with the motion-design skill before coding each scene.

### Anti-slop rules (checked at every design review)

1. No gradient backgrounds, glows, neon, glassmorphism, lens flares, or purple-to-blue anything.
2. No emoji or stock icons in the video UI. Icons, if any, come from one consistent outline set.
3. Maximum two typefaces (Plex Sans family + Plex Mono counts as one system). Sentence case everywhere.
4. Text contrast at least 4.5:1 against its background; nothing smaller than 28 px on 1080p.
5. Every number that changes (eval, clock, move numbers) uses tabular figures so it does not jitter.
6. No element exists only to fill space. If a region is empty, it stays empty.
7. Run `npx impeccable detect` and `/impeccable audit` on the gallery stills; fix every finding or record why it is intentional.

### Avoiding the mass-produced look

YouTube does not monetize content that looks templated and mass-produced (section 10). The template stays consistent, but each video must differ visibly and substantively:

- Four board themes, one per series (section 11), not per video at random.
- Cold opens always start on that game's own key moment, so no two videos open the same way.
- Chapter structure follows the game (a 25-move miniature has no endgame chapter).
- Thumbnails show that game's critical position and that beat's mascot pose.

### The four templates

| Template | Status | Look | Use |
| --- | --- | --- | --- |
| Studio | Build now | Dark, broadcast-calm, board-first | All long-form until Editorial exists |
| Shorts | Build now | Studio tokens, vertical, bigger type | Every Short |
| Editorial | After return | Light "paper" background, serif display titles, more white space | Opening explainers, historical games |
| Arena | After return | Bolder, player colors, clocks prominent | Tournament and rivalry content |

### Thumbnails (Thumbnail composition, 1280 × 720)

- The critical position, cropped to the 4 × 4 area where it happens, with the decisive arrow.
- The mascot large on one side, in that beat's pose.
- At most 4 words of text, Plex Sans Condensed, high contrast. Never repeat the title verbatim.
- Render with `npx remotion still`; check legibility at 320 × 180 (how it shows in search results).

## 7. Mascot

The mascot is an original character owned by ChessCode, built as a layered SVG rig in React so every pose is deterministic and editable in code. It is not the Claude logo, not a Duolingo lookalike and not an OpenAI Codex pet used as-is.

### Why not borrow one

- Claude: Anthropic's [trademark guidelines](https://www.anthropic.com/legal/trademark-guidelines) allow its marks only where Anthropic specifically permits, prohibit altering them, and prohibit implying affiliation. A Claude spark mascot on a monetized channel fails all three.
- Duolingo's Duo: a protected character. Take the lessons, not the look. Duolingo's redesign started from the silhouette, locked color and species, and found Duo's best angle before adding motion ([Duolingo blog](https://blog.duolingo.com/reshaping-duo/)). Rive's case study on Duolingo's Lily shows the other lesson: separate head and body animations that combine, so idle motion never visibly loops ([Rive blog](https://rive.app/blog/duolingo-s-ai-powered-video-call-brings-lily-to-life)).
- OpenAI Codex pets: `/hatch` in the Codex app generates an AI pet ([Engadget](https://engadget.com/2162796/openai-introduces-ai-generated-pets-for-its-codex-app)). OpenAI's [terms](https://openai.com/policies/terms-of-use/) assign output rights to the user, but AI-generated art has uncertain copyright protection and others may get similar output. The owner may hatch a pet and share it as a mood reference, but the final character is redrawn as an original vector design.

### Concept (default; the owner picks from 3 concept sheets)

Pyaada (प्यादा, Hindi for pawn): a small, round pawn who is sure he deserves to be promoted. The name works in both languages and the running gag writes itself.

- Silhouette: the pawn's ball head and flared base, slightly squashed (wider than a real pawn) so it reads at 120 px tall. Readable as a black fill alone.
- Face: two large oval eyes with pupils and eyelids, simple eyebrows, one mouth shape layer. Eyes do most of the acting.
- Arms: two short noodle arms (two segments each) that appear only when a pose needs them.
- Palette: body in one warm off-white, one darker shade for the base and shading, dark ink for the face, plus one accent for his paper crown. Three colors and an accent, no gradients.
- Signature prop: a paper crown sticker he made himself, worn slightly crooked.
- Personality: confident, dramatic, wrong about his own importance. Never mean to players.

Two alternates for the concept sheets: a tiny knight who only moves in L-shapes even when walking across the screen; an "engine bot", a small square robot with an eval-bar face that fills with emotion. Both follow the same rig rules.

### Why an SVG rig and not Rive or Lottie

Remotion supports Rive through `@remotion/rive` ([docs](https://www.remotion.dev/docs/rive)), but its documented API covers artboard and animation playback, not frame-by-frame state-machine input. Driving reactions from spec beats needs exact frame control, so the rig is plain React SVG with spring interpolation. Rive can be revisited later as an upgrade for richer acting, after a prototype proves frame-accurate control.

### Rig structure

```
mascot/
  Pyaada.tsx         renders the rig from a PoseState
  parts/             Body, Base, Eyes (L, R), Brows, Mouth, Arms, Props
  poses.ts           named pose targets (below)
  idle.ts            breathing, bob, blink: seeded, never Math.random
  react.ts           beat -> pose sequence with timing
  speech.tsx         speech bubble with type-on text and voice blips
```

A `PoseState` is plain numbers: body squash/stretch, lean angle, head tilt, eye open (0 to 1), pupil x/y, brow angle and height, mouth shape id, arm angles, prop id. A pose is a target `PoseState`; the rig springs from the current state to the target. Squash and stretch always conserve volume.

### Pose library (minimum for launch)

| Pose | Used by beat | Notes |
| --- | --- | --- |
| `idle` | always | Breath 1.0 to 1.02 scale, blink every 2.5 to 5 s (seeded) |
| `wave` | intro | Only in ColdOpen end and Outro |
| `thinking` | `opening_exit` | Hand on chin, eyes up |
| `side_eye` | `mistake` | Pupils slide, brow down |
| `facepalm` | `blunder` 1 to 2 | Arm up, eyes shut |
| `faint` | `blunder` 3 | Falls backward out of frame, slides back in 1.5 s later |
| `slow_clap` | `brilliant` | 3 claps synced to sfx |
| `screaming` | `missed_win` | Mouth wide, squash-stretch shake |
| `shocked` | `comeback` | Jump, eyes huge |
| `party` | `comeback`, wins | Paper hat swap, confetti from `@remotion/shapes` |
| `checks_watch` | `long_think` | Taps wrist |
| `sweating` | `time_scramble` | One sweat drop, looping |
| `binoculars` | `king_walk` | Prop |
| `jealous` | `promotion` | Clutches his paper crown |
| `mic_drop` | `checkmate` | Mic falls with a bounce |
| `bow` | `resign` | Polite bow |
| `point` | Outro CTA | Points at the end-screen area |

### Behavior rules

- Size: about 200 px tall in Studio (bottom-right), about 260 px in Shorts (below the board).
- Enters with the first beat or in ColdOpen; never leaves during Playback except for `faint`.
- Reaction timing per section 8: react on frame 7 after the freeze, bubble text from frame 10, bubble stays 1.8 s plus 60 ms per character, then idle.
- The mouth flaps while the bubble types; a short pitched voice blip (one of 6 samples, seeded) plays per word. No spoken mascot voice.
- The mascot never covers the board, the eval bar or captions. Layout tests check bounding boxes.

### Creation workflow

1. Claude Code draws 3 concept sheets as SVG (front pose, silhouette, 6 expressions each), using frontend-design and Impeccable `shape`.
2. The owner picks one (human checkpoint) and may mark changes on the sheet.
3. Build the rig and the 17 poses; render `MascotSheet` (all poses in a grid) and a 20-second reaction reel.
4. `design-critic` reviews; the owner approves the reel.
5. Freeze the rig: after approval, pose changes need a new reel review.

## 8. Humor system

The humor is driven by the game data, not written per video: Python detects beats from engine and clock data, the script step writes one short mascot line per beat, and Remotion turns each beat into a timed reaction. This is what lets 100 videos be funny without a human writing 100 scripts.

### Roles: straight man and clown

- The narrator (TTS voice) is the straight man: clear, confident, explains the chess properly.
- The mascot is the clown: it never explains chess, it only reacts. It speaks through a speech bubble with short text plus a non-verbal "gibberish" voice blip (Animal Crossing style), so no second TTS voice is needed and the joke works in both languages.
- The joke is in the contrast: the narrator calmly says "Black's position is now lost", and the mascot has already fainted.

### Beat taxonomy and triggers

All evals are from the moving side's perspective, in pawns. Thresholds live in `config/beats.yaml` so they can be tuned without code changes.

| Beat type | Trigger (computed in Python) | Default mascot pose | Effects |
| --- | --- | --- | --- |
| `blunder` | Eval drop ≥ 2.0, or a winning eval (≥ +2) becomes ≤ 0 | `facepalm` (intensity 3: `faint`) | Board shake 6 frames, red flash on the moved piece, instant replay of the move |
| `mistake` | Eval drop 1.0 to 2.0 | `side_eye` | Subtle red underline on the move in the move list |
| `brilliant` | Best or near-best move (drop ≤ 0.3) that gives up ≥ 2 points of material | `slow_clap` | Gold glint on the piece, "!!" stamp |
| `missed_win` | Best move had eval ≥ +3, played move ≤ +1 | `screaming` | Ghost arrow showing the missed move |
| `comeback` | Side was ≤ -3 within the last 20 plies and is now ≥ 0 | `shocked` then `party` | Eval bar whip animation |
| `long_think` | Move took ≥ 15% of the remaining clock or ≥ 5 min (clock data required) | `checks_watch` | Clock icon pulse |
| `time_scramble` | Mover has ≤ 60 s left | `sweating` | Clock turns red, ticking sfx under voice |
| `king_walk` | King makes its 3rd non-castling move before move 30 with queens on | `binoculars` | King trail drawn on board |
| `promotion` | Any promotion; underpromotion is intensity 3 | `jealous` (running gag: the pawn mascot wants promotion) | Crown sparkle |
| `checkmate` / `resign` | Final ply | `mic_drop` or `bow` | Freeze frame, outro sting |
| `opening_exit` | First ply not in book | `thinking` | "Out of theory" label |

### Pacing rules (enforced in Python, re-checked in QA)

- At least 20 s between any two beats; at least 60 s between two intensity-3 beats.
- 8 to 14 beats in a 10-minute video; Shorts get 2 to 4.
- Never the same pose twice in a row. Never the same mascot line twice in one video, and no line reused within 10 videos of the same language (tracked in `data/line_history.sqlite`).
- Priority when beats compete for the same window: `checkmate` > `blunder` > `brilliant` > `missed_win` > `comeback` > the rest. Lower-priority beats are dropped, not delayed.
- Comic timing for intensity ≥ 2: freeze on the move for 6 frames, mascot reacts on frame 7, line appears on frame 10, narration resumes after the reaction (Python leaves a 900 ms gap in the narration timeline before the next segment).

### Joke writing rules (given to the script LLM verbatim)

1. The joke is about the move or the position, never about the player as a person, their nationality, age, gender or rating.
2. Mascot lines: at most 8 words in English, 10 words in Hindi. One idea per line.
3. Hindi lines are natural spoken Hindi with common chess English kept in English (fork, pin, blunder, checkmate), the way Indian chess creators actually talk. No textbook Hindi.
4. No profanity, no slurs, no politics, no religion, no sexual content, no meme formats that date quickly.
5. Running gags are encouraged and tracked: the mascot wants to be promoted; the mascot distrusts the h-pawn; the mascot thinks every rook lift is "too aggressive".
6. If the model cannot write a line that follows these rules, it picks one from the reviewed line bank instead.

### Line bank (fallback and quality floor)

- `content/lines/en.yaml` and `content/lines/hi.yaml`: at least 25 lines per beat type per language, written once by an LLM, then reviewed and edited by the owner before Nov 1.
- The script step may write fresh lines, but QA (section 12) checks them against the rules above with a cheap model and falls back to the bank on any violation.

### What "funny but professional" means here

- The board, typography and narration stay serious and clean at all times. Comedy lives only in the mascot, the sound effects and the timing.
- No meme images, no stock reaction GIFs, no zoom-punch on every move. Effects fire only on beats.
- Every effect has an off switch per template in `theme.ts` (for example, Editorial may disable board shake).

## 9. Batch rendering on GitHub Actions

One GitHub Actions job produces one finished video end to end: build the spec, render, QA, upload as scheduled. A matrix fans out across videos, so nothing large ever moves between jobs and no video files are stored on GitHub. GitHub is used only while the owner is still online; nothing runs on a schedule during the offline period.

### Runner facts (GitHub docs, checked Oct 27, 2026)

| Repo type | Standard Linux runner | Minutes (Free plan) | Notes |
| --- | --- | --- | --- |
| Public | 4 vCPU, 16 GB RAM, 14 GB SSD | Free, unmetered | Logs and artifacts are publicly visible |
| Private | 2 vCPU, 8 GB RAM, 14 GB SSD | 2,000 min/month, then $0.006/min | 500 MB artifact storage |

Other limits: 6 h per job, 256 jobs per matrix, 20 concurrent jobs on the Free plan, artifacts kept 90 days by default. Scheduled workflows in public repos are disabled after 60 days without activity, which is one more reason not to depend on schedules ([runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners), [limits](https://docs.github.com/en/actions/reference/limits), [billing](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions)).

### Repo visibility decision

Default: a private repo with paid overage minutes. The cost is small, and scripts, titles and the release calendar stay private. Rough math: 104 videos × 120 runner-minutes each ≈ 12,500 minutes, about $63 after the free 2,000. Re-check with the real render time from week 1.

Alternative: a public repo for faster free 4-vCPU runners. Only choose it if the owner accepts that logs reveal upcoming titles and games. Never upload video files as artifacts in a public repo.

Fallback if Actions is too slow: Remotion Lambda, about $0.10 to $0.11 for a 10-minute HD video at their example settings plus AWS setup ([cost example](https://www.remotion.dev/docs/lambda/cost-example)).

### Workflows

| File | Trigger | Does |
| --- | --- | --- |
| `ci.yml` | push, pull request | `pytest`, `tsc --noEmit`, ESLint, schema export check, `npx impeccable detect remotion/src`, and a 10-second smoke render of a fixture spec |
| `batch.yml` | `workflow_dispatch` with inputs `batch_id`, `video_ids` (JSON list), `upload` (true/false) | The matrix: one job per video, stages below |
| `collect.yml` | `workflow_run` after `batch.yml` | Downloads each job's small result JSON, appends to `data/upload_log.csv`, commits it, writes a run summary |
| `audit.yml` | `workflow_dispatch` | Runs the Codex and Antigravity audit prompts read-only against a ref and stores reports in `audits/` (optional; the owner can also run them locally) |

### `batch.yml` job steps (per video)

1. Checkout; set up Python 3.12 and Node 22.
2. Restore caches with `actions/cache`: `node_modules`, Chrome Headless Shell, Stockfish binary, `data/engine_cache.sqlite`, the TTS audio cache. Keys include lockfile hashes.
3. Install Linux deps for Chrome (the Ubuntu 24.04 package list from [Remotion's Linux page](https://www.remotion.dev/docs/miscellaneous/linux-dependencies)) and run `npx remotion browser ensure`.
4. `python -m chesscode run --video <id> --until emit` (all Python stages).
5. `npx remotion render` and `npx remotion still` (section 5 commands).
6. Automated QA (section 12). On failure, mark the video `failed_qa` and stop; never upload.
7. If `upload` is true: idempotent upload (section 10). Writes `result.json`: `{video_id, status, youtube_id, publish_at, qa_score, render_seconds}`.
8. Upload `result.json`, `thumb.png` and the QA contact sheet as a small artifact (under 5 MB). Never the MP4.

### Matrix settings

- `strategy.fail-fast: false` so one bad video does not cancel the batch.
- `max-parallel: 16`, leaving headroom under the 20-job limit for CI.
- `timeout-minutes: 300` per job, under the 6-hour hard limit.
- `concurrency: group: video-${{ matrix.video_id }}`, so the same video can never render or upload twice at once.

### Secrets (repository secrets, never in code or logs)

`ANTHROPIC_API_KEY`, the chosen TTS keys, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`. Scripts must never echo them. The refresh token must come from an OAuth app in production status (section 10).

### Batching plan

- Batch 0: 2 videos (1 EN, 1 HI), `upload=false`. Measure render time and runner minutes; fix everything.
- Batch 1: the 5 videos for Gate D, `upload=true`. Verify in YouTube Studio.
- Batches 2 to N: floor tier first, about 20 videos per batch so a bad batch costs hours, not days. Target tier after the floor is complete.

## 10. YouTube upload and scheduling

Every video is uploaded with `privacyStatus: private` and a `publishAt` date, so YouTube publishes it on schedule with nobody online. The first thing to build and test, before any template work, is one real scheduled upload from the real Google Cloud project, because an unverified project may lock uploads to private permanently.

### Day-1 risk test (do this before anything else)

YouTube's help page says videos uploaded through an unverified API service are locked as private, with no appeal, and the fix is an audit or re-uploading another way ([help](https://support.google.com/youtube/answer/7300965)). The current API reference pages say the opposite. Nobody can resolve this by reading, so test it:

1. Upload one short throwaway video through the API from the project the pipeline will use, private, with `publishAt` one day ahead.
2. In YouTube Studio, check whether it shows as Scheduled or as Locked.
3. Let it publish (or move the time to an hour ahead) and confirm it actually goes public.

If it is locked: submit the [Audit and Quota Extension Form](https://support.google.com/youtube/contact/yt_api_form) the same day, and plan the fallback (section 14): render everything anyway and schedule the floor tier through YouTube Studio's own uploader by hand.

### OAuth (one owner, one channel)

- Use an OAuth client of type Desktop app, scopes `youtube.upload` and `youtube` (needed for thumbnails and playlists).
- Move the OAuth consent screen to "In production" before generating the refresh token. In "Testing" status, refresh tokens expire 7 days after consent ([Google Cloud help](https://support.google.com/cloud/answer/15549945)), which would break every upload after a week.
- A production app that is not verified shows a warning screen; the owner clicks through it once. Verification is not needed for a single owner account.
- Store the refresh token as a GitHub secret. Write a `chesscode auth check` command that refreshes the token and calls `channels.list?mine=true` as a health check; run it at the start of every batch.

### Quota (checked Oct 27, 2026)

YouTube changed upload quota twice: in Dec 2025 the upload cost dropped from about 1,600 units to about 100, and since Jun 1, 2026 `videos.insert` has its own bucket of 100 calls a day, separate from the 10,000-unit pool for everything else ([quota costs](https://developers.google.com/youtube/v3/determine_quota_cost), [revision history](https://developers.google.com/youtube/v3/revision_history)). Quota resets at midnight Pacific time.

| Call | Cost | Per video | Notes |
| --- | --- | --- | --- |
| `videos.insert` | 1 call from the 100/day upload bucket | 1 | Assume failed attempts also count |
| `thumbnails.set` | 50 units | 50 | Max file size raised to 50 MB in Sep 2026 |
| `playlistItems.insert` | 50 units (verify) | 50 | One playlist per series |
| `playlistItems.list` (dedupe check) | 1 unit | 1 to 2 | Paged, 50 items a page |

About 100 units per video from the 10,000 pool means the pool, not the upload bucket, caps a day at roughly 95 videos. The uploader stops at 60 videos per Pacific day to leave room for retries, and resumes the next day.

### Upload call details

- Resumable upload (the Google API client's `MediaFileUpload(resumable=True)`), retry 5xx and network errors with exponential backoff, maximum 5 tries.
- `snippet`: `title` (≤ 100 characters), `description` (≤ 5,000), `tags`, `categoryId` 20 (Gaming; owner may switch to 27, Education), `defaultLanguage` and `defaultAudioLanguage` (`en` or `hi`).
- `status`: `privacyStatus: private`, `publishAt` (UTC ISO 8601; only valid while private and never published), `selfDeclaredMadeForKids: false`, `containsSyntheticMedia` (see below).
- After insert: `thumbnails.set`, then `playlistItems.insert`. If either fails, the video stays scheduled and the step is retried by `chesscode upload --repair`.
- Guard: refuse to upload if `publishAt` is in the past or less than 2 hours ahead. A past `publishAt` publishes immediately.

### Idempotency (never upload twice)

- Every description ends with a footer line `ccid: <video_id>`.
- Before inserting, check `data/upload_log.csv`, then page through the channel's uploads playlist for that `ccid`. Found means skip and record the existing YouTube id.
- After an ambiguous failure (timeout during upload), run the uploads-playlist check before retrying.

### Description template

1. Two-line hook specific to the game (from the script step).
2. Chapters: first line `00:00`, at least three chapters, each at least 10 s long (from `chapters[]`).
3. Game facts: players, event, year, opening, result. "Game source: Lichess" where applicable.
4. Series and playlist link, channel subscribe line.
5. Credits (music, piece set) as required by their licenses.
6. `ccid:` footer.

### Shorts

YouTube classifies square or vertical videos up to 3 minutes as Shorts automatically; there is no API flag ([help](https://support.google.com/youtube/answer/15424877)). Add `#Shorts` to the title or description anyway; it is harmless.

### Disclosure and monetization policy

- Altered or synthetic content: disclosure is required for realistic content, such as making a real person appear to say or do something. Non-realistic content is exempt ([policy](https://support.google.com/youtube/answer/14328491)). A TTS narrator over an animated board with a cartoon mascot does not depict real people, so the default is `containsSyntheticMedia: false`. The owner may set it to true; it costs nothing.
- Inauthentic content: since Jul 15, 2025, YouTube does not monetize "inauthentic" content, including AI content built from generic templates that looks mass-produced ([policy](https://support.google.com/youtube/answer/1311392)). The same intro and outro are fine when the body of each video differs. Defenses built into this spec: a different game and real analysis in every video, game-specific cold opens and chapters, series with distinct focus, rotating board themes per series, written-not-translated Hindi. The script-step check in section 12 rejects scripts that are mostly generic filler.

### Manual Studio steps (cannot be done by API)

End screens cannot be set through the API. Option A: skip them during the offline period. Option B: the owner adds an end screen by hand to the first few videos of each series (Studio can import an end screen from another video). The Outro scene reserves the space either way.

## 11. Content plan and publishing calendar

Four evergreen series, each with its own board theme and playlist, published on a fixed weekly rhythm from Nov 16, 2026 to Feb 15, 2027. Each Short is cut from a beat of an upcoming long-form game and goes out before it, as a teaser linked to the full video.

### Series

| Series | What each video is | Why it works for this channel | Board theme |
| --- | --- | --- | --- |
| Legendary Games | One famous game, start to finish (Opera Game, Immortal Game, Game of the Century, Kasparov vs Topalov 1999) | Evergreen search demand; strong story arcs | Bone and slate (default) |
| Indian Chess Heroes | A defining game by an Indian player (Anand, Humpy, Harikrishna, Gukesh, Praggnanandhaa, Arjun, Divya) | Strong for the Hindi audience; national pride without news dependence | Walnut |
| Opening Explained | One opening's main idea, taught through one model game | Search traffic for opening names; educational value | Cool grey |
| Blunder Hall of Fame | Famous blunders by strong players, with the mascot at full volume | Best Shorts material; comedy-first | Warm sand |

The owner approves the final `games.yaml` list (at least 70 games, about 18 per series) before the batch week. Claude Code drafts it with notes on why each game is interesting and which beats it contains.

### Weekly rhythm (times in UTC; IST is UTC+5:30)

| Day | Floor tier | Target tier adds |
| --- | --- | --- |
| Monday | Short (EN) 12:30 |  |
| Tuesday | Long-form game A (EN) 18:30 |  |
| Wednesday | Short (HI) 12:30 |  |
| Thursday | Long-form game A (HI) 13:30 (7:00 pm IST) |  |
| Friday | Short (EN or HI, alternating) 12:30 |  |
| Saturday |  | Long-form game B (EN) 18:30 |
| Sunday |  | Long-form game B (HI) 13:30; Short 12:30 |

These times are starting points chosen for Indian evening and US daytime viewing. The calendar lives in `config/calendar.yaml`, so the owner can shift them without code changes.

### Calendar rules (enforced by the `metadata` stage and re-checked by `spec-validator`)

- The EN and HI versions of one game (`pair_id`) never publish on the same day.
- Series rotate: no series runs more than two long-form weeks in a row.
- A Short from game X publishes 1 to 3 days before game X's long-form in the same language.
- No two uploads at the same time on the same day.
- Floor-tier slots are filled first, earliest date first, so if the batch stops early the gaps are at the end of the schedule, not scattered.

### Titles

- Specific and curious, never false: "He sacrificed his queen on move 17 (and it worked)" beats "INSANE chess game!!".
- The script step proposes 3 titles; a cheap model scores them against rules (≤ 70 characters, no all-caps words, no claims the game does not support); the best one is used.
- Hindi titles are written in Hindi with chess terms in English, the way Indian chess search queries are typed. Optionally add the English player names in Latin script for search.

## 12. QA, testing and audit gates

No video uploads unless every automated check passes; nothing passes on a model's say-so alone. Machine checks catch the objective failures, cheap vision models catch visual defects, and the owner reviews a short batch page instead of watching 100 videos.

### Code tests (run in `ci.yml`)

- Python: the `pytest` suites in section 4.
- Remotion unit tests (Vitest): `msToFrame` round trips; `positions.ts` produces the same FEN as chess.js for every ply of 20 fixture games, including castling, en passant, promotion and underpromotion; eval-to-bar mapping is monotonic and clamped; caption pages never split a word.
- Visual regression: render every `TemplateGallery` still and compare with approved baselines (pixel diff under a set threshold). A baseline changes only through a reviewed commit.
- Layout test: at every beat frame of the fixture specs, the mascot's and bubble's bounding boxes do not intersect the board, eval bar or captions.

### Automated per-video checks (in `batch.yml`, written to `qa.json`)

| Check | How | Fails when |
| --- | --- | --- |
| Spec valid | JSON Schema + pacing + calendar rules | Any violation |
| Moves real | SAN guard (section 4) | Any move not in the game or engine line |
| Mascot lines clean | `line-checker` (Haiku) against section 8 rules | Any violation not replaced from the line bank |
| Script is specific | Haiku scores specificity; plus a count of concrete squares, moves and plans | Under the threshold in `config/qa.yaml` |
| Audio levels | ffmpeg `loudnorm` analysis per segment | Outside -14 ± 1 LUFS, or true peak above -1 dBTP |
| No dead air | ffmpeg `silencedetect` | Silence over 2.5 s outside planned pauses |
| No black frames | ffmpeg `blackdetect` | Any black segment outside cuts |
| File correct | `ffprobe` | Not h264 / yuv420p / AAC, wrong size, fps or duration (± 1 frame) |
| Frames look right | Frames at each beat and every 30 s, as a contact sheet, reviewed by `qa-frames` (Haiku, vision) | Blank board, cut-off text, overlapping UI, empty boxes in Devanagari text, mascot missing on a beat |
| Thumbnail legible | Thumbnail downscaled to 320 × 180, reviewed by `qa-frames` | Text unreadable or position unclear |

A failed video is not uploaded and is listed in the run summary with the failing check. Re-render after a fix; never override a failed check in the pipeline.

### Owner review (about 10 minutes per batch)

`collect.yml` publishes a review page per batch as a static HTML file in the repo (or an artifact): one row per video with thumbnail, title, publish date, series, QA score and contact sheet. The owner:

- watches the first full EN and HI videos end to end (Gate C, before any batch);
- after that, opens 1 in 5 contact sheets and all thumbnails;
- unschedules or deletes anything wrong directly in YouTube Studio. Scheduled videos stay private until their date, so there is time to fix.

### Audit gates

The four gates (A to D) and the auditor commands are in section 0. Each gate also has a fixed checklist the auditors must answer:

- Gate A: Is the schema complete for every scene? Can any timing produce overlapping audio or a move shown mid-word? Do beat thresholds match the game data on the 10 golden games?
- Gate B: Does the template pass the anti-slop rules in section 6? Is everything readable at 1080p and on a phone? Is motion consistent?
- Gate C: Is the chess correct throughout? Are the jokes on-rules? Would this video look mass-produced to a reviewer?
- Gate D: Can the uploader double-upload, publish early, or fail silently? Are secrets ever logged? Does the ledger match Studio?

## 13. Milestones and timeline

Nine build days, a feature freeze on Nov 6, then render and upload: the floor tier must be scheduled by Nov 11 so the last four days are spare capacity, not crunch.

&#91;embedded content: build and batch timeline · Oct 28 to Nov 15, 2026\]

Workstreams overlap on purpose: the Python contract, the mascot and the templates run in parallel in separate worktrees, joined by the JSON contract.

### Milestones and exit criteria

| # | Milestone | Done when |
| --- | --- | --- |
| M1 | Day-1 risk tests | One API upload is scheduled and confirmed not locked; OAuth app is in production; TTS samples for 3 providers in EN and HI are ready for the owner; one 60-second Remotion render has been timed on Actions |
| M2 | Contract + Python pipeline | Zod schema and JSON Schema exported; all Python stages emit valid specs for the 10 golden games; Gate A triaged |
| M3 | Owner content prep | `games.yaml` has 70+ approved games; line banks reviewed; voices chosen |
| M4 | Mascot | Owner picked a concept; 17 poses render in `MascotSheet`; reaction reel approved |
| M5 | Studio + Shorts templates | Gallery stills and a 60-second clip pass Impeccable audit and Gate B; owner approves; features frozen Nov 6 |
| M6 | Batch 0 | One full EN and one full HI video rendered on Actions, watched end to end by the owner; Gate C triaged |
| M7 | First uploads | 5 videos scheduled through the pipeline, ledger matches Studio; Gate D triaged |
| M8 | Floor tier | All 65 floor-tier uploads scheduled |
| M9 | Target tier | As many of the remaining 39 as time allows, earliest dates first |

### If the schedule slips

- Mascot late: ship videos with the mascot in `idle` and a reduced pose set (facepalm, slow clap, shocked, party), and add the rest after return.
- Templates late: Gate B is the hard line on Nov 6. Past it, the floor tier renders with the legacy pipeline and the new uploader (section 14).
- Rendering slow: stop the target tier, never the floor tier.

## 14. Risks, fallbacks and open decisions

The two risks that could end the plan are an API upload lock and the Remotion build running late; both have a tested fallback that still gets the floor tier scheduled by Nov 15.

### Risks

| Risk | Impact | Early signal | Mitigation and fallback |
| --- | --- | --- | --- |
| API uploads locked private (unverified project) | Nothing publishes | Day-1 test (section 10) | Submit audit form the same day. Fallback: schedule the floor tier by hand in YouTube Studio (bulk upload, set date per video), about 3 to 4 hours of owner time |
| OAuth token expires while offline | Uploads stop mid-batch | `auth check` fails | Consent screen in production before generating the token; all uploads finish before Nov 15 anyway |
| Remotion build runs late | No new look by the batch week | Gate B not passed by Nov 6 | Freeze features on Nov 6. Ship the floor tier with whatever Studio state passes Gate B; if Gate B fails, render the floor tier with the old Pillow pipeline plus the new uploader |
| Render too slow on Actions | Backlog not finished | Batch 0 render time | Paid private-runner minutes; larger runners; Remotion Lambda; drop to floor tier |
| Hindi TTS sounds unnatural | Weak Hindi videos | TTS bake-off | Try another provider; if none is good, keep HI for Shorts only and publish EN long-form with Hindi captions |
| Wrong chess in narration | Credibility loss | SAN guard, golden tests | Regenerate the segment; never upload with a failed guard |
| Demonetized as inauthentic content | No revenue | Policy review at Gate C | Real per-game analysis, variety rules (sections 6, 11), specificity check |
| Asset licence problem (pieces, fonts, music) | Takedown or claim | `CREDITS.md` review at Gate D | CC0/MIT/OFL assets only; music only from sources that allow monetized use, with required credits in descriptions |
| Spam comments while offline | Messy channel | n/a | Before leaving, set Studio comment moderation to hold potentially inappropriate comments (or hold all) |
| Lichess rate limits | Slow fetch | HTTP 429 | One request at a time, 60 s back-off, PGN cache |

### Open decisions for the owner

- [ ] Mascot concept (Pyaada or an alternate) and any changes to it.
- [ ] TTS provider and voices for EN and HI, after the bake-off.
- [ ] Repo visibility: private with paid minutes (default) or public.
- [ ] Palette: new Studio palette or the existing ChessCode colors.
- [ ] YouTube category: Gaming (default) or Education.
- [ ] `containsSyntheticMedia`: false (default) or true.
- [ ] End screens: skip, or add by hand to the first video of each series.
- [ ] Exact return date, to confirm the 13-week window.
- [ ] Final `games.yaml` list and the reviewed line bank.

## 15. Sources

All pages were checked on Oct 27, 2026. Items the research could not confirm are marked as such in the sections that use them (for example, the 1080p render benchmark, the API private-lock conflict, and Hindi timestamp quality per TTS provider).

**Rendering**

- [Remotion license](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md) and [company license pricing](https://www.remotion.pro/license)
- [Remotion CLI render options](https://www.remotion.dev/docs/cli/render), [performance](https://www.remotion.dev/docs/performance), [browser ensure](https://www.remotion.dev/docs/cli/browser/ensure), [Linux dependencies](https://www.remotion.dev/docs/miscellaneous/linux-dependencies)
- [Rendering on GitHub Actions (SSR page)](https://www.remotion.dev/docs/ssr), [Lambda cost example](https://www.remotion.dev/docs/lambda/cost-example)
- [calculateMetadata](https://www.remotion.dev/docs/calculate-metadata), [createTikTokStyleCaptions](https://www.remotion.dev/docs/captions/create-tiktok-style-captions), [loadFont](https://www.remotion.dev/docs/google-fonts/load-font), [font loading errors](https://www.remotion.dev/docs/troubleshooting/font-loading-errors), [@remotion/rive](https://www.remotion.dev/docs/rive)
- [Lichess asset licenses (COPYING.md)](https://raw.githubusercontent.com/lichess-org/lila/master/COPYING.md), [Lichess database (CC0)](https://database.lichess.org/)

**Claude Code skills and agents**

- [Superpowers](https://github.com/obra/superpowers), [Impeccable](https://github.com/pbakaus/impeccable), [Remotion agent skills](https://www.remotion.dev/docs/ai/skills), [LottieFiles motion-design-skill](https://github.com/LottieFiles/motion-design-skill)
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents), [headless mode](https://code.claude.com/docs/en/headless)
- [Codex CLI non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [Codex models](https://learn.chatgpt.com/docs/models)
- [Antigravity surfaces (Google Cloud blog)](https://cloud.google.com/blog/topics/developers-practitioners/choosing-your-surface-antigravity-20-antigravity-cli-antigravity-ide-or-antigravity-sdk), [Gemini CLI](https://github.com/google-gemini/gemini-cli)

**YouTube and GitHub**

- [YouTube API quota costs](https://developers.google.com/youtube/v3/determine_quota_cost), [revision history](https://developers.google.com/youtube/v3/revision_history), [quota and compliance audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits), [videos resource](https://developers.google.com/youtube/v3/docs/videos)
- [Videos locked as private](https://support.google.com/youtube/answer/7300965), [Shorts length](https://support.google.com/youtube/answer/15424877), [altered or synthetic content](https://support.google.com/youtube/answer/14328491), [inauthentic content policy](https://support.google.com/youtube/answer/1311392)
- [OAuth consent screen publishing status](https://support.google.com/cloud/answer/15549945)
- [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners), [Actions limits](https://docs.github.com/en/actions/reference/limits), [Actions billing](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions)

**Mascot and voice**

- [Reshaping Duo (Duolingo)](https://blog.duolingo.com/reshaping-duo/), [Rive and Duolingo's Lily](https://rive.app/blog/duolingo-s-ai-powered-video-call-brings-lily-to-life), [Rive pricing](https://rive.app/pricing)
- [Codex pets (Engadget)](https://engadget.com/2162796/openai-introduces-ai-generated-pets-for-its-codex-app), [OpenAI terms of use](https://openai.com/policies/terms-of-use/), [Anthropic trademark guidelines](https://www.anthropic.com/legal/trademark-guidelines)
- [ElevenLabs API pricing](https://elevenlabs.io/pricing/api), [ElevenLabs timestamps](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps), [Azure speech synthesis events](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis), [Sarvam pricing](https://docs.sarvam.ai/api/getting-started/pricing.md), [Google TTS release notes](https://docs.cloud.google.com/text-to-speech/docs/release-notes)
