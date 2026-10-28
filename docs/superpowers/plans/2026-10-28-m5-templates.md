# M5 Studio + Shorts Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder `StudioVideo` with the full Studio scene sequence, add `ShortsVideo`, `Thumbnail` and `TemplateGallery`, beat effects, music bed and sfx, so a 1.1.0 spec renders a finished video. Frozen Nov 6 after Gate B and owner approval.

**Architecture:** One pure function, `scenes/timeline.ts`, cuts the spec into scene ranges (ms) from `narration[].kind`, `cold_open`, `key_moments` and `duration_ms`. Each composition maps ranges to `<Sequence>`s of scene components. Scenes reuse the core layer (`board/`, `ui/`, `theme/`) and the mascot layer (`src/mascot`, from M4). Effects in `fx/` are driven only by `beats[].fx` and `at_ms`, and each has a per-template off switch.

**Tech Stack:** Remotion 4.0.539 (pinned), React 19, TypeScript, chess.js, `@remotion/captions`, `@remotion/media`, `@remotion/shapes`, Vitest.

**Spec:** `docs/SPEC.md` sections 5 (scenes, Shorts, rendering), 6 (layout, motion, anti-slop, thumbnails), 8 (beat effects, "funny but professional"), 12 (layout test, visual regression). Contract: `remotion/src/spec/schema.ts` (1.1.0, read-only). Fixture: `spec/fixtures/cc-2026-0001-en/`. Approved deviations: `docs/ROADMAP.md` owner decisions log (Shorts board 864, black piece ink, four hue families, blunder `#E8545A`).

## Global Constraints

- Read `remotion-best-practices` before any component; plan each scene's timing and choreography with the `motion-design` skill; first build of each scene goes through Impeccable `shape`/`craft`, every still through `critique` + `audit`.
- Determinism: no `Math.random`, `Date.now`, network. Timing only via `msToFrame`/`frameToMs`.
- Never edit `src/spec/schema.ts`; a missing field is reported, not invented.
- Assets imported from `src/assets/` (bundler), never `staticFile`, except spec-folder files (`narration[].audio`, `music.track`, which use `staticFile` with `--public-dir=<spec folder>`).
- Studio layout (1920×1080): 8 px grid, 96 px outer margins; board 800×800 at the left, vertically centred; eval bar 24 px wide, 16 px left of the board; right column from x = 1000: player cards top, move list middle (current move centred, 9 rows), mascot box bottom-right (about 200 px tall); captions in the lower right column, never over the board; chapter cards and key-moment labels top-left of the right column.
- Shorts layout: `theme/layout.ts` `shortsLayout` boxes exactly; nothing important in the right 120 px or bottom 340 px.
- Motion: tokens in `theme/motion.ts` only; piece 280 ms; UI enter 240–360 ms; one element enters at a time (stagger 60 ms); scene changes are hard cuts or a short slide.
- Anti-slop (spec 6): no gradients, glows, neon, glass, emoji, stock icons; sentence case; contrast >= 4.5:1; nothing under 28 px at 1080p; tabular figures for every changing number; empty regions stay empty.
- Comedy lives only in the mascot, sfx and timing; board, type and narration stay clean. Effects fire only on beats; each effect has an off switch in `theme/templates.ts`.
- Sfx never louder than the voice (peak <= -12 dBFS, under narration volume); music bed at `music.volume`, ducked to `music.duck_under_voice` while narration plays, 200 ms ramps.
- Each task ends with `npx vitest run` and `npx tsc --noEmit` green from `remotion/`.

## Review Focus

1. A 25-move miniature (Opera Game) with no endgame chapter and only 2 key moments → timeline must not create empty chapter cards or zero-length scenes.
2. A key moment that starts while a beat reaction is still on screen → mascot bubble and key-moment label must not overlap (layout test at every beat frame).
3. Black at the bottom (winner is Black) in the KeyMoment alternative line and the thumbnail crop → arrows and crop must follow orientation.
4. Hindi (Devanagari) in player cards, chapter cards, verdict and thumbnail text at 28 px minimum → no clipped matras, no overflow (gallery stills in HI).
5. A Short whose beat is the final ply (checkmate) → the loop (last frame ≈ first frame) still holds, and the freeze frame does not stall the ending.

---

### Task 1: Scene timeline

**Files:** Create `remotion/src/scenes/timeline.ts`; Test `timeline.test.ts`

**Interfaces:**
- Produces: `type SceneKind = "cold_open" | "title" | "player_intro" | "playback" | "key_moment" | "verdict" | "outro"`; `type SceneRange = { kind: SceneKind; startMs: number; endMs: number; keyMoment?: KeyMoment }`; `sceneRanges(spec: VideoSpec): SceneRange[]` — ordered, contiguous, covering `0..duration_ms`; non-ply narration kinds define their scene's range; `key_moments[]` cut their own ranges out of playback; `outro` runs to `duration_ms`.
- [ ] Tests on the fixture and on synthetic specs: contiguous and non-overlapping; no zero-length range; every `key_moments[i]` maps to one `key_moment` range with matching ms; a spec with no `chapter` narration yields no chapter cards (Task 3 consumes `chapterCardsFor(spec)` from here: `{ title, startMs }[]` from `spec.chapters` excluding the first).
- [ ] Commit.

### Task 2: Board time control and alternative lines

**Files:**
- Modify: `remotion/src/board/Board.tsx`
- Create: `remotion/src/board/LineBoard.tsx`
- Test: `remotion/src/board/lineBoard.test.ts`

**Interfaces:**
- Produces:
  - `Board` gains optional `atMs?: number` (draw the game state at this ms instead of the current frame; used by ColdOpen remapping and freeze frames) and `hideArrows?: boolean`. Existing callers unchanged.
  - `lineStates(fenBefore: string, uci: string[]): PlyState[]` and `LineBoard: FC<{ fen: string; line: string[]; startMs: number; stepMs: number; size: number; orientation: "white"|"black"; theme: BoardTheme }>` — animates the alternative line with the same 280 ms piece motion and an arrow for the next move.
- [ ] Tests: `lineStates` matches chess.js FENs for a line with a capture, a castle and a promotion; illegal UCI throws with the move named.
- [ ] Commit.

### Task 3: UI pieces for the Studio frame

**Files:** Create `remotion/src/ui/{MoveList,PlayerCard,ChapterCard,LowerLabel,Clock}.tsx`; Test `ui/moveList.test.ts`

**Interfaces:**
- `MoveList: FC<{ spec: VideoSpec; box: Box }>` — 9 visible rows, current move centred, numbering `12.` / `12...`, Plex Mono tabular, move class colour only on `mistake`/`blunder`/`brilliant`/`best` of the current ply; `mistake` beat gets the subtle underline (`move_underline` fx).
- `moveRows(plies, currentPly): { no: number; white?: string; black?: string; current: "w"|"b"|null }[]` (pure, tested: windowing at the start, middle and end of a game).
- `PlayerCard: FC<{ player: Player; side: "white"|"black"; lang }>` — name, title, rating or nothing when null, country code when present, `fact` in PlayerIntro only.
- `ChapterCard`, `LowerLabel` (key-moment label), `Clock` (`clock_ms` formatted `m:ss`, tabular; red + pulse via fx).
- [ ] Commit.

### Task 4: Beat effects

**Files:** Create `remotion/src/fx/{index,shake,flash,stamp,glint,trail,ghostArrow,sparkle,label}.tsx`, `remotion/src/theme/templates.ts`; Test `fx/fx.test.ts`

**Interfaces:**
- `templates.ts`: `type TemplateFx = Record<Fx, boolean>`; `templateFx: Record<"studio"|"shorts", TemplateFx>` (all on for both now).
- `fxWindows(beats: Beat[], fps: number): { fx: Fx; beat: Beat; from: number; to: number }[]` — frames per effect: `board_shake` 6 frames from `at_ms`; `red_flash` 8; `replay_move` = re-run the ply's 280 ms move once after the freeze; `freeze_frame` 6 (uses `freezeAt` from `src/mascot` once M4 lands; until then this module's own 6-frame rule); `gold_glint`/`stamp_brilliant` 24; `ghost_arrow` 60; `eval_whip` handled by `EvalBar` already; `clock_pulse`/`clock_red` until the ply ends; `king_trail` 90; `crown_sparkle` 30; `out_of_theory_label` 60.
- `BoardFx: FC<{ spec; size; orientation; template }>` overlay drawn above the board (shake is a translate on the board wrapper, max 6 px, decaying).
- [ ] Tests: windows deterministic; disabled fx produce no window; shake offset is 0 outside its window.
- [ ] Commit.

### Task 5: Studio scenes and composition

**Files:**
- Create: `remotion/src/scenes/{ColdOpen,TitleCard,PlayerIntro,Playback,KeyMoment,Verdict,Outro}.tsx`, `remotion/src/audio/{MusicBed,Sfx}.tsx`, `remotion/src/assets/sfx/*.mp3`, `scripts/fetch_sfx.py`
- Modify: `remotion/src/compositions/StudioVideo.tsx`, `remotion/public/CREDITS.md`

Scene content (spec 5 table): ColdOpen plays `cold_open.ply_from..ply_to` remapped onto its range, mascot reaction, the `hook` line; TitleCard 2.5 s title, players, year (from `game.date`); PlayerIntro two cards with `fact`; Playback board + eval bar + move list + captions + chapter cards + mascot; KeyMoment slower replay: `LineBoard` with `key_moments[i].line`, label, mascot; Verdict result, turning point (board at `verdict.turning_point_ply` with its move highlighted), accuracy per side (tabular); Outro mascot sign-off and an empty reserved end-screen area (right two thirds), nothing drawn there.

- `MusicBed: FC<{ music; narration }>` — volume callback per frame with 200 ms ramps; a missing or placeholder track renders silence without failing.
- `Sfx: FC<{ beats }>` — one `<Audio>` per beat with non-null `sfx`, at `at_ms`, from `src/assets/sfx/<id>.mp3`. Ids from `config/beats.yaml` `sfx`: `oof_01 hmm_01 ding_01 gasp_01 whip_01 tick_01 tick_02 sparkle_01 sting_01 sting_02`.
- `fetch_sfx.py`: downloads CC0 packs from kenney.nl (Interface Sounds, Impact Sounds, UI Audio), picks one file per id, converts to 48 kHz MP3, peak <= -12 dBFS, and records each in `CREDITS.md` with source URL and CC0. Generated (synthesised) fallbacks are allowed for any id without a good match.
- [ ] Layout test `scenes/layout.test.ts`: at every beat frame of the fixture, the boxes of mascot, bubble, captions, move list, labels do not intersect the board or eval bar.
- [ ] Render the fixture: `npx remotion render StudioVideo build/m5/studio.mp4 --props=../spec/fixtures/cc-2026-0001-en/video_spec.json --public-dir=../spec/fixtures/cc-2026-0001-en`.
- [ ] Commit.

### Task 6: Shorts and thumbnail

**Files:** Create `remotion/src/compositions/{ShortsVideo,Thumbnail}.tsx`; Modify `Root.tsx`; Test `compositions/thumbnail.test.ts`

- `ShortsVideo`: 1080×1920 from `shortsLayout`; hook text (`cold_open.hook`) visible from frame 0 for the first second; one beat; captions `mode="shorts"`; mascot in `boxes.mascot` (about 260 px); the last 10 frames ease the board back to the first frame's position so the loop holds; `calculateMetadata` rejects a non-shorts spec.
- `Thumbnail`: 1280×720 still; board cropped to the 4×4 window with lower-left `thumbnail.crop_origin` (respecting orientation) at `thumbnail.ply`, the ply's decisive arrow; mascot large on one side in `thumbnail.pose`; `thumbnail.text` in Plex Sans Condensed, high contrast, <= 4 words.
- `cropWindow(origin: string, orientation): string[]` (16 squares), tested for both orientations.
- [ ] Render a still and check legibility downscaled to 320×180.
- [ ] Commit.

### Task 7: Mascot integration (after M4 merges to `main`)

- [ ] Merge `main` into `ws/m5-templates`; place `MascotLayer` in ColdOpen, Playback, KeyMoment, Outro (Studio) and ShortsVideo; `Thumbnail` uses `Pyaada` with `POSES[thumbnail.pose]`; `freeze_frame` uses `freezeAt`.
- [ ] Layout test re-run with real mascot bounds. Commit.

### Task 8: Gallery, design review, Gate B `[HUMAN]`

**Files:** Create `remotion/src/compositions/TemplateGallery.tsx`; Modify `Root.tsx`, `.github/workflows/ci.yml` (add `npx impeccable detect remotion/src`)

- `TemplateGallery` (`panel` prop): one still per scene type in EN and HI, plus Shorts hook, Shorts beat and thumbnail = the 6+ stills for the owner.
- [ ] `design-critic` (Opus): Impeccable `critique` + `audit` on all stills and frames from the 60 s clip; fix list applied; re-run until no high-severity findings.
- [ ] Gate B: `agy -p` audit and a fresh Claude auditor against the Gate B checklist (anti-slop, readable at 1080p and on a phone, motion consistent) → `audits/gateB-*.md`; triage in `audits/TRIAGE.md`.
- [ ] `[HUMAN]` owner approves 6 stills + one 60 s clip, and the palette decision (new Studio palette or `#161B26`/`#1E2533`). Freeze on approval (no later than Nov 6).
