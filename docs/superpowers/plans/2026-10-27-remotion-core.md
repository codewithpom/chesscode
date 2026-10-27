# Remotion Core (Board, Eval Bar, Captions) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The reusable drawing layer every template needs: theme + motion tokens, self-hosted fonts, the chess board with move animation, the eval bar, and captions, reviewable as gallery stills.

**Architecture:** Pure React/SVG components in `remotion/src/{theme,board,ui}` driven only by the `VideoSpec` props and the current frame. `positions.ts` replays the PGN once (memoized) and components look state up by frame. No scene composition here (M5); a `CoreGallery` composition shows each component in isolation for design review.

**Tech Stack:** Remotion 4.0.539 (all `remotion`/`@remotion/*` pinned exactly), React 19, TypeScript, Zod 4.5.4, chess.js 1.4.0, `@remotion/captions`, Vitest 5.

**Spec:** `docs/SPEC.md` sections 5 and 6, `PRODUCT.md`. Contract: `remotion/src/spec/schema.ts` (read-only here). Fixture: `spec/fixtures/cc-2026-0001-en/`.

## Global Constraints

- Read the `remotion-best-practices` skill before any component; plan each animation with the `motion-design` skill.
- Determinism: no `Math.random`, `Date.now`, or network during render; seeded `random()` from `remotion` only.
- All ms→frame via `msToFrame` / `frameToMs` in `src/spec/time.ts`; nowhere else.
- Never edit `src/spec/schema.ts`. If a field is missing, stop and report.
- Render with `--public-dir=<spec folder>`; app assets (fonts, pieces) are imported from `src/assets/` via bundler imports, not `staticFile`, so they work with any public dir.
- Fonts: IBM Plex Sans, Plex Sans Condensed, Plex Mono, Plex Sans Devanagari (SIL OFL), `.woff2` in `src/assets/fonts/`, loaded with `FontFace` inside `delayRender`/`continueRender`. Never `loadFont()` without explicit `weights` and `subsets`.
- Pieces: a CC0 or MIT SVG set (rhosgfx CC0 preferred). Never cburnett, GPL/AGPL or CC BY-NC-SA sets. Every asset recorded in `remotion/public/CREDITS.md` with source URL and license.
- Studio palette: bg `#0F1115`, surface `#171A21`, hairline `#262A33`, text `#ECEEF2`, muted `#9097A3`; semantic only for move quality: best `#3DD68C`, brilliant `#F2A93B`, mistake `#F5A524`, blunder `#E5484D`.
- Motion: enter `cubic-bezier(0.22, 1, 0.36, 1)`, one exit easing, one UI spring with no visible overshoot; piece move 280 ms; UI enter 240–360 ms; stagger 60 ms.
- Anti-slop (section 6): no gradients, glows, neon, glass; no emoji; sentence case; contrast ≥ 4.5:1; nothing under 28 px at 1080p; tabular figures for changing numbers.
- Layout (Studio 1920×1080): board 800×800 at left, vertically centered, outer margin 96 px; eval bar 24 px wide, 16 px left of the board. (Shorts: board 960×960, eval bar horizontal and thin above it.)
- Each task ends with `npx vitest run` and `npx tsc --noEmit` green, run from `remotion/`.

## Review Focus

1. Black-at-bottom orientation (winner is Black): squares, coordinates, arrows and animations must all flip → Task 3 test + gallery still.
2. Promotion with capture on the last rank (`exd8=Q+`): captured piece fades, pawn slides, then swaps → Task 3 test.
3. Mate evals both signs and a `cp` of ±10000-like values: bar clamped, never NaN → Task 4 test.
4. Caption page boundary landing on a Hindi word with a nukta or conjunct (e.g. `क्ष`, `ड़`) → Task 5 test asserts token text equals the spec word.
5. Seeking (rendering a frame in the middle of a move without previous frames) must give the same pixels as sequential rendering → Task 3 test calls the frame→state function at arbitrary frames.

---

### Task 1: Theme and motion tokens, fonts

**Files:**
- Create: `remotion/src/theme/tokens.ts`, `theme/motion.ts`, `theme/boardThemes.ts`, `theme/fonts.ts`, `remotion/src/assets/fonts/*.woff2`, `remotion/public/CREDITS.md`
- Test: `remotion/src/theme/tokens.test.ts`

**Interfaces:**
- Produces:
  - `tokens: { color: {bg, surface, hairline, text, muted, best, brilliant, mistake, blunder}, space: (n: number) => number /* 8 px grid */, font: {sans, condensed, mono, devanagari}, size: {min: 28, ...} }`
  - `boardThemes: Record<BoardTheme, {light: string; dark: string; coord: string; lastMove: string; check: string}>` — `bone_slate` light `#E8E2D4` dark `#6E7F86`; `walnut`, `cool_grey`, `warm_sand` chosen by the builder within the anti-slop rules and flagged for design review.
  - `motion: { enter: (t: number) => number; exit: (t: number) => number; uiSpring: SpringConfig; pieceMoveMs: 280; captureFadeMs: 120; uiEnterMs: 300; staggerMs: 60 }` (`Easing.bezier(0.22, 1, 0.36, 1)` from remotion)
  - `useFonts(): void` — registers all four families with `FontFace` + `delayRender`; `fontFor(lang: "en" | "hi", role: "ui" | "title" | "mono"): string`
  - `contrast(a: string, b: string): number` (WCAG ratio)

- [ ] **Step 1: Failing tests** `test every text/background pair in tokens has contrast >= 4.5`, `test boardThemes covers all four BoardTheme values`, `test fontFor("hi","ui") includes "IBM Plex Sans Devanagari"`, `test spring has no overshoot` (sample `spring()` with `uiSpring` over 60 frames; max ≤ 1.0005).
- [ ] **Step 2:** `npx vitest run src/theme` → FAIL.
- [ ] **Step 3:** Implement; download the Plex `.woff2` files (weights 400, 500, 600; Latin + Devanagari) from the IBM Plex GitHub release, record license in `CREDITS.md`.
- [ ] **Step 4:** PASS; `npx tsc --noEmit` clean.
- [ ] **Step 5:** Commit `feat(remotion): theme, motion tokens and self-hosted fonts`.

### Task 2: `positions.ts`

**Files:**
- Create: `remotion/src/board/positions.ts`, `remotion/src/board/fixtures/games.ts` (20 PGNs incl. castling both sides, en passant, promotion, underpromotion, capture-promotion; the main session supplies them)
- Test: `remotion/src/board/positions.test.ts`

**Interfaces:**
- Produces:
  - `type PieceId = string` (stable per physical piece across the game, e.g. `"wN-g1"`, so React keys survive moves)
  - `type PlacedPiece = { id: PieceId; type: "p"|"n"|"b"|"r"|"q"|"k"; color: "w"|"b"; square: string }`
  - `type PlyState = { fen: string; pieces: PlacedPiece[]; move: { from: string; to: string; captured: PieceId | null; castleRook: { id: PieceId; from: string; to: string } | null; promotion: "q"|"r"|"b"|"n" | null; enPassantSquare: string | null } | null }` (index 0 = start position, `move` null)
  - `buildPositions(pgn: string): PlyState[]` — memoized by pgn string
- Contract check: `buildPositions(spec.game.pgn)[i].fen === spec.plies[i-1].fen_after` for every ply of the fixture.

- [ ] **Step 1: Failing tests** `test FEN matches chess.js for every ply of 20 fixture games`, `test fixture spec fen_after matches`, `test castling moves king and rook ids`, `test en passant captures the pawn on the correct square`, `test promotion keeps the pawn id and sets promotion`, `test piece ids are unique per ply`, `test memoized (same array reference on second call)`.
- [ ] **Step 2–4:** FAIL → implement → PASS.
- [ ] **Step 5:** Commit `feat(remotion): replay PGN into per-ply piece states`.

### Task 3: Board

**Files:**
- Create: `remotion/src/board/Board.tsx`, `Square.tsx`, `Piece.tsx`, `Arrows.tsx`, `Highlights.tsx`, `boardState.ts`, `remotion/src/assets/pieces/*.svg`
- Test: `remotion/src/board/boardState.test.ts`

**Interfaces:**
- Consumes: `buildPositions`, `boardThemes`, `motion`, `msToFrame`.
- Produces:
  - `boardStateAt(frame: number, fps: number, plies: Ply[], positions: PlyState[]): { ply: number; pieces: Array<PlacedPiece & { x: number; y: number; opacity: number; scale: number }>; highlights: Highlight[]; arrows: Arrow[] }` — pure; `x, y` in square units (0..7) from White's view; a ply starts animating at `msToFrame(show_at_ms)` and lasts `pieceMoveMs`; captured piece opacity fades to 0 over the last `captureFadeMs`; castling rook moves in parallel; promotion swaps type at the end with scale 1 → 1.12 → 1 over 160 ms; en passant removes the pawn on `enPassantSquare`.
  - `<Board spec={VideoSpec} size={number} />` — 64 `rect`s, coordinates (Plex Mono, ≥ 28 px equivalent at Studio size), last-move highlight (soft), check (`boardThemes[x].check` on the king square, no glow filters), max 2 arrows (`best`, `threat`, `missed` colors from tokens; `missed` dashed). Orientation from `spec.board.orientation` (flip in render, not in state).
- [ ] **Step 1: Failing tests** `test piece at rest before show_at`, `test midway at 140 ms is halfway with eased progress`, `test captured piece opacity 0 at end`, `test castling rook arrives with king`, `test en passant pawn removed`, `test capture-promotion swaps at end`, `test boardStateAt is pure: same frame twice equals and random-order frames equal sequential` (review focus 5), `test never more than 2 arrows`.
- [ ] **Step 2–4:** FAIL → implement → PASS.
- [ ] **Step 5:** Commit `feat(remotion): SVG board with move animation`.

### Task 4: Eval bar

**Files:**
- Create: `remotion/src/ui/EvalBar.tsx`, `remotion/src/ui/winprob.ts`
- Test: `remotion/src/ui/winprob.test.ts`

**Interfaces:**
- `winPct(e: { cp: number | null; mate: number | null }): number` — `50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1)`; mate > 0 → 100, mate < 0 → 0. Same constant as the Python pipeline (`pipeline/chesscode/winprob.py`).
- `evalLabel(e): string` — `"+1.4"`, `"−0.3"` (U+2212), `"M3"` / `"−M3"`, `"0.0"`.
- `<EvalBar spec orientation="vertical" | "horizontal" length={number} thickness={number} />` — white share = `winPct` springed (`uiSpring`, clamped 0..100) from the previous ply's value starting at `show_at_ms`; on a frame inside a `blunder` beat, use a faster whip spring (`stiffness` × 3, still no overshoot) then settle; label in Plex Mono tabular figures.

- [ ] **Step 1: Failing tests** `test monotonic in cp`, `test clamped 0..100 for cp ±100000`, `test mate signs`, `test symmetric`, `test labels`, `test no NaN for {cp: 0}`.
- [ ] **Step 2–4:** FAIL → implement → PASS.
- [ ] **Step 5:** Commit `feat(remotion): eval bar`.

### Task 5: Captions

**Files:**
- Create: `remotion/src/ui/captions.ts`, `remotion/src/ui/Captions.tsx`
- Test: `remotion/src/ui/captions.test.ts`

**Interfaces:**
- `toCaptions(narration: NarrationSegment[]): Caption[]` — one `@remotion/captions` `Caption` per word: `{ text: " " + w, startMs, endMs, timestampMs: null, confidence: null }` (leading space: spaces are the delimiters).
- `captionPages(narration, mode: "long" | "shorts"): TikTokPage[]` — `createTikTokStyleCaptions({ captions, combineTokensWithinMilliseconds })` with `1200` for long-form, `400` for Shorts (tuned so long-form fits two lines, Shorts 1–3 words).
- `<Captions spec mode />` — long-form: lower area under the right column (x ≥ 1000, never over the board), max two lines, current word in `tokens.color.text`, others `muted`; Shorts: 1–3 words, large, centered above the board. Font per language via `fontFor`.

- [ ] **Step 1: Failing tests** `test every token text starts with a space`, `test pages never split a word` (concatenated page tokens == source words, EN and a Hindi narration containing `क्षमा`, `पड़ा`, `ज़्यादा`), `test shorts pages have 1 to 3 words`, `test page timing within its segment`.
- [ ] **Step 2–4:** FAIL → implement → PASS.
- [ ] **Step 5:** Commit `feat(remotion): captions from word timings`.

### Task 6: CoreGallery + design review

**Files:**
- Create: `remotion/src/compositions/CoreGallery.tsx`; modify `remotion/src/Root.tsx` (register `CoreGallery` stills only; leave `StudioVideo` as is), `spec/fixtures/cc-2026-0002-hi/` is **not** created here; Hindi caption still uses an inline Hindi narration sample in the gallery props.

**Interfaces:**
- `CoreGallery` is a `Still`-style composition with prop `panel: "board-bone_slate" | "board-walnut" | "board-cool_grey" | "board-warm_sand" | "board-black-bottom" | "eval-states" | "captions-en" | "captions-hi" | "captions-shorts"`, 1920×1080 (shorts panel 1080×1920), using the fixture spec.

- [ ] **Step 1:** Render all panels: `npx remotion still CoreGallery ../build/gallery/<panel>.png --props='{"panel":"<panel>"}' --public-dir=../spec/fixtures/cc-2026-0001-en`.
- [ ] **Step 2:** `npx impeccable detect src` → record output.
- [ ] **Step 3:** Dispatch `design-critic` on `build/gallery/*.png` (Impeccable `critique` + `audit` against section 6 and `PRODUCT.md`); apply every fix or record why it is intentional in `audits/TRIAGE.md`.
- [ ] **Step 4:** Re-render; full `npx vitest run` + `npx tsc --noEmit` green.
- [ ] **Step 5:** Commit `feat(remotion): core gallery stills`.

### Audit

Codex read-only branch review (`codex exec -s read-only -o audits/remotion-core-codex.md "<review prompt>"`), triaged in `audits/TRIAGE.md` before merge.
