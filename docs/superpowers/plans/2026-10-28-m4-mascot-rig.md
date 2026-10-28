# M4 Mascot Rig (Pyaada) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pyaada as a deterministic React SVG rig with 17 poses, seeded idle motion, beat-driven reactions with a speech bubble and voice blips, one `MascotLayer` that scenes place in a box, a `MascotSheet` review grid and a 20-second reaction reel for owner approval.

**Architecture:** A pose is a target `PoseState` (plain numbers). `react.ts` turns `spec.beats` into a per-frame pose timeline; the rig springs from the previous pose to the target with the shared UI spring (`theme/motion.ts`); `idle.ts` adds breathing, bob and blinks from `random(seed)`. `Pyaada.tsx` draws layered parts from a `PoseState`. Scenes only use `MascotLayer`.

**Tech Stack:** Remotion 4.0.539 (pinned), React 19, TypeScript, `@remotion/shapes` (confetti), `@remotion/media` Audio, Vitest.

**Spec:** `docs/SPEC.md` section 7 (rig structure, pose table, behavior rules), section 8 (comic timing, beat→pose), section 6 (motion, anti-slop). Approved concept: `design/mascot/pyaada.svg` + `design/mascot/BRIEF.md`; part geometry and expression math in `design/mascot/build_sheets.py` (`Face` dataclass, `eye`, `brows`, mouth paths).

## Global Constraints

- Determinism: no `Math.random` / `Date.now`; seeds from `beat_id` / `video_id` via `random()` from `remotion`.
- All timing via `msToFrame` / `frameToMs` (`src/spec/time.ts`). Never edit `src/spec/schema.ts`.
- Palette exactly as the approved sheet: body warm off-white, one darker base/shade, dark ink face and outline, one accent for the paper crown. No gradients, glows or effects. One outline weight.
- Silhouette and proportions as `pyaada.svg` (head radius 58 on a 180-wide base; crown 52 wide, 12° clockwise, right of centre).
- Squash and stretch conserve volume: `scaleX * scaleY === 1` (within 1e-9).
- Sizes: about 200 px tall in Studio, about 260 px in Shorts (fit inside the given box, bottom-aligned).
- Comic timing (spec 8): for intensity >= 2 the frame freezes for 6 frames from `at_ms`; the mascot reacts on frame 7; bubble text from frame 10; bubble stays 1.8 s + 60 ms per character; then back to `idle`. Intensity 1: react at `at_ms`, no freeze, same bubble rule.
- `faint`: falls backward out of the box, slides back in 1.5 s later.
- Mouth flaps while the bubble types; one voice blip per word, chosen by seeded random from 6 samples. No spoken voice.
- The mascot and bubble never leave their box (the box is guaranteed clear of board, eval bar and captions by the scene layouts).
- Assets imported from `src/assets/` (bundler imports), never `staticFile` (renders use `--public-dir=<spec folder>`).
- Each task ends with `npx vitest run` and `npx tsc --noEmit` green from `remotion/`.

## Review Focus

1. Two beats close together (20 s apart, the pacing minimum) where the first bubble is still up → second reaction must replace it cleanly, no overlap of bubbles.
2. A Hindi line (Devanagari, 10 words) in the 260 px Shorts box → bubble wraps on spaces only, never mid-word, never outside the box.
3. A beat at `at_ms` 0 or within the last 2 s of the video → no negative frames, no crash.
4. Same pose twice in a row is avoided by Python, but `alt_poses` may land on `faint` → `faint` re-entry must finish before the next beat's pose.
5. Render on Linux CI: blips must be in the bundle (imports), not in the public dir.

---

### Task 1: PoseState and the pose library

**Files:**
- Create: `remotion/src/mascot/poseState.ts`, `remotion/src/mascot/poses.ts`
- Test: `remotion/src/mascot/poses.test.ts`

**Interfaces:**
- Produces:
  - `type PoseState = { squash: number; lean: number; headTilt: number; eyeOpen: number; pupilX: number; pupilY: number; eyeScale: number; browAngle: number; browY: number; browRY: number; mouth: MouthId; armL: number; armR: number; arms: ArmsId; prop: PropId; propLift: number; offsetX: number; offsetY: number; sweat: number }` (`squash` > 1 = squashed: `scaleX = squash`, `scaleY = 1 / squash`).
  - `type MouthId = "smile" | "flat" | "o" | "wide" | "frown" | "smirk" | "open_talk"`; `ArmsId = "none" | "chin" | "face" | "clap" | "up" | "wrist" | "point" | "hold"`; `PropId = "crown" | "party_hat" | "mic" | "binoculars" | "watch" | "none"`.
  - `POSES: Record<Pose, PoseState>` for every value of the `Pose` enum in `spec/schema.ts`.
  - `lerpPose(a: PoseState, b: PoseState, t: number): PoseState` (numbers lerp; ids switch at `t >= 0.5`).
- [ ] Test: `POSES` has a key for every `Pose.options`; every pose's `eyeOpen` in [0,1]; `lerpPose(a,b,0)` equals `a` and `(a,b,1)` equals `b`; `scaleOf(squash)` product is 1.
- [ ] Implement, matching the expressions on the approved sheet (`build_sheets.py` faces map field-for-field to `PoseState`).
- [ ] Commit.

### Task 2: Parts and `Pyaada.tsx`

**Files:**
- Create: `remotion/src/mascot/parts/{Body,Base,Eyes,Brows,Mouth,Arms,Props}.tsx`, `remotion/src/mascot/Pyaada.tsx`
- Test: `remotion/src/mascot/Pyaada.test.tsx` (render to static markup)

**Interfaces:**
- Produces: `Pyaada: React.FC<{ state: PoseState; height: number }>` — an `<svg>` with `viewBox` from the concept sheet, layers in order base, body, head, eyes, brows, mouth, arms, prop; ids stable.
- [ ] Test: renders every pose without throwing; `prop: "none"` renders no prop group; output for the same state is byte-identical twice.
- [ ] Port geometry from `pyaada.svg` / `build_sheets.py`; arms are two-segment ink noodles only when `arms !== "none"`.
- [ ] Render `MascotSheet` early (Task 6 stub) and compare visually to `design/mascot/pyaada.png`. Commit.

### Task 3: Seeded idle

**Files:** Create `remotion/src/mascot/idle.ts`; Test `idle.test.ts`

**Interfaces:**
- Produces: `idleAt(frame: number, fps: number, seed: string): Partial<PoseState>` — breath scale 1.00–1.02 (as `squash` around 1), small bob in `offsetY`, blink (eyeOpen dips to 0 over 4 frames) every 2.5–5 s from `random(seed + n)`.
- [ ] Test: same inputs → same output; over 60 s at 30 fps, every gap between blink starts is within [75, 150] frames; breath never outside [1.00, 1.02].
- [ ] Commit.

### Task 4: Reactions timeline

**Files:** Create `remotion/src/mascot/react.ts`; Test `react.test.ts`

**Interfaces:**
- Consumes: `Beat` from `spec/schema.ts`.
- Produces:
  - `type Reaction = { beat: Beat; freezeFrom: number; freezeTo: number; reactFrame: number; bubbleFrom: number; bubbleTo: number }` — frames per the comic-timing constraint; `freezeFrom = freezeTo` for intensity 1; `bubbleTo` clamped so it ends before the next reaction's `reactFrame`.
  - `reactionsFor(beats: Beat[], fps: number, durationInFrames: number): Reaction[]`
  - `poseAt(frame: number, reactions: Reaction[], fps: number, seed: string): PoseState` — idle before the first reaction and after each bubble ends; spring (`uiSpring` from `theme/motion.ts`) from the previous target to the beat's pose starting at `reactFrame`; `faint` special: `offsetX` out of the box over 12 frames, back in over 12 frames starting 1.5 s after `reactFrame`.
  - `freezeAt(frame: number, reactions: Reaction[]): number | null` — the frame the board should hold, for scenes.
- [ ] Tests: intensity-3 beat at 10 000 ms, fps 30 → freeze 300–306, react 306, bubble from 309, bubble length 54 frames + 60 ms × chars; beat at 0 ms gives no negative frames; two beats 20 s apart → first bubble ends before the second react frame; `faint` is back in the box by `reactFrame + 45 + 12`.
- [ ] Commit.

### Task 5: Speech bubble and blips

**Files:**
- Create: `remotion/src/mascot/speech.tsx`, `scripts/make_blips.py`, `remotion/src/assets/sfx/blip_{1..6}.mp3`
- Test: `remotion/src/mascot/speech.test.ts`

**Interfaces:**
- Produces:
  - `typedText(line: string, frame: number, from: number, fps: number): string` — reveals text at about 12 characters per second, rounded down to word boundaries so Devanagari clusters never split.
  - `SpeechBubble: React.FC<{ line: string; from: number; to: number; box: Box; language: "en" | "hi" }>` — Plex Sans (or Plex Sans Devanagari), >= 28 px, ink on off-white, one tail toward the mascot, inside `box`.
  - `blipFrames(line: string, from: number, fps: number, seed: string): { frame: number; sample: 1|2|3|4|5|6 }[]` — one per word.
- [ ] `make_blips.py`: 6 original blips (60–90 ms, pitched sine with fast attack/decay, different pitches), generated with ffmpeg from `imageio_ffmpeg`, peak <= -12 dBFS (always under the voice).
- [ ] Tests: `typedText` never returns a partial word (EN and a Devanagari conjunct line); `blipFrames` count equals word count and is deterministic.
- [ ] Commit.

### Task 6: `MascotLayer`, `MascotSheet`, reaction reel

**Files:**
- Create: `remotion/src/mascot/MascotLayer.tsx`, `remotion/src/mascot/index.ts`, `remotion/src/compositions/MascotSheet.tsx`, `remotion/src/compositions/MascotReel.tsx`
- Modify: `remotion/src/Root.tsx` (register both)
- Test: `remotion/src/mascot/layer.test.ts`

**Interfaces (M5 scenes depend on these exact exports from `src/mascot/index.ts`):**
- `MascotLayer: React.FC<{ spec: VideoSpec; box: Box; height: number }>` — reads `useCurrentFrame()`, draws `Pyaada` bottom-aligned in `box` with `poseAt`, the bubble for the active reaction, and blip `<Audio>`s.
- `reactionsFor`, `freezeAt` re-exported.
- `MascotSheet`: 1920×1080 still, all 17 poses in a labelled grid (pose name in Plex Mono 28 px).
- `MascotReel`: 1920×1080, 20 s, 30 fps; a synthetic spec (blunder i3 faint, brilliant, missed_win, comeback, promotion, checkmate) on a plain `#0F1115` background with a mock board box, showing the timing rules.
- [ ] Test: for every beat frame in the fixture spec, the mascot and bubble bounds stay inside `box` (Studio and Shorts boxes).
- [ ] Render: `npx remotion still MascotSheet build/m4/sheet.png`, `npx remotion render MascotReel build/m4/reel.mp4`.
- [ ] `design-critic` reviews sheet + reel frames; fixes applied. Audit: Codex read-only (`codex exec -s read-only`, warn about the caveman proxy) or a fresh Claude reviewer.
- [ ] `[HUMAN]` owner approves the reel. After approval the rig is frozen.
