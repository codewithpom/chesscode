# Mascot Concept Sheets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three original mascot concept sheets the owner can choose from: Pyaada (default), an L-move knight, and an engine bot, each as a hand-built SVG drawn with the same layered parts the M4 rig will use.

**Architecture:** One SVG per concept in `design/mascot/`, built from named groups (`body`, `base`, `eye-l`, `eye-r`, `brow-l`, `brow-r`, `mouth`, `arm-l`, `arm-r`, `prop`) so the chosen concept ports straight into `remotion/src/mascot/parts/`. Rasterized to PNG with cairosvg; one private Artifact page compares the three.

**Tech Stack:** Hand-written SVG, Python cairosvg for PNG, Impeccable `shape`, `frontend-design`.

**Spec:** `docs/SPEC.md` section 7 (concept, rig rules), section 6 (anti-slop, palette), `PRODUCT.md`.

## Global Constraints

- Original character: not the Claude spark, not Duolingo-like (no green owl shapes, no round feathered body), not an AI-generated image traced.
- Three colors plus one accent per concept: warm off-white body, one darker shade for base/shading, dark ink for the face, one accent (Pyaada: paper crown). No gradients, glows or filters.
- Silhouette readable as a black fill alone at 120 px tall.
- Eyes do most of the acting: two large ovals with pupils and eyelids, simple brows, one mouth layer. Arms are two-segment noodles that appear only when a pose needs them.
- Each sheet, 2400×1600: front pose (large), silhouette test (black fill at 120 px and at 400 px), 6 expressions (neutral, side_eye, facepalm, shocked, slow_clap, sweating), palette swatches with hex, name + one-line personality. Sheet typography: IBM Plex Sans, sentence case.
- Same layer names across all three concepts.

## Review Focus

1. Silhouette at 120 px: the pawn and knight must not read as generic blobs; check against a real Staunton silhouette at the same size.
2. Expressions must differ by eyes/brows first, not by props, so they read at Studio size (≈ 200 px).
3. Crooked crown must still read as a crown at 120 px, not as hair.
4. The engine bot's eval-bar face must not look like a battery icon or a phone status bar.
5. Hindi name प्यादा set in Plex Sans Devanagari on the Pyaada sheet must render without broken conjuncts.

---

### Task 1: Shape brief

- [ ] **Step 1:** Run `/impeccable shape` with the brief from section 7 + `PRODUCT.md` (serious board, funny mascot; Indian and international audience). Record the chosen proportions (head:base ratio, eye size as % of head width, crown angle) in `design/mascot/BRIEF.md`.
- [ ] **Step 2:** Commit `docs(mascot): shape brief`.

### Task 2: Pyaada sheet

**Files:** Create `design/mascot/pyaada.svg`
- [ ] **Step 1:** Draw front pose with the layer groups above; build the 6 expressions by changing only eye/brow/mouth/arm groups.
- [ ] **Step 2:** Rasterize: `python -c "import cairosvg; cairosvg.svg2png(url='design/mascot/pyaada.svg', write_to='design/mascot/pyaada.png')"`; view the PNG; check silhouette at 120 px.
- [ ] **Step 3:** Commit `feat(mascot): Pyaada concept sheet`.

### Task 3: Knight sheet

**Files:** Create `design/mascot/knight.svg` — tiny knight who only moves in L-shapes; add a small L-path diagram showing how he crosses the screen.
- [ ] **Step 1–3:** as Task 2.

### Task 4: Engine-bot sheet

**Files:** Create `design/mascot/engine-bot.svg` — small square robot whose face is an eval bar that fills with emotion; show the face at +, 0, − and mate states.
- [ ] **Step 1–3:** as Task 2.

### Task 5: Critique, compare, checkpoint

- [ ] **Step 1:** Dispatch a fresh `design-critic` subagent on the three PNGs (Impeccable `critique`; checks the Global Constraints and Review Focus). Apply fixes; re-render.
- [ ] **Step 2:** Build `design/mascot/compare.html` (three sheets side by side, silhouettes row, expression row) and publish it as a private Artifact.
- [ ] **Step 3:** Commit `feat(mascot): concept comparison`.
- [ ] **Step 4: `[HUMAN]` STOP.** Owner picks a concept and marks changes. M4 (rig + 17 poses) is planned after the choice.
