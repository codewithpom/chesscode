# ChessCode v2 roadmap (M1 to M9)

Source of truth: `docs/SPEC.md`. Hard deadline: **all floor-tier uploads scheduled by Nov 11, everything done by Nov 15, 2026.** Feature freeze **Nov 6**. When a nice-to-have competes with the deadline, the deadline wins.

`[HUMAN]` marks an owner checkpoint: work on that path stops until the owner answers. Work on other paths continues.

## Dependency graph

```
Phase 0 (done: a702d81) ── contract, skeleton, agents
  ├── M1 Day-1 risk ──────────────┬──────────────────────────────┐
  │     auth, upload test, TTS,   │                              │
  │     Actions timing            ▼                              │
  ├── M2 pipeline ──(voice needs M1 tts)── Gate A ──┐            │
  ├── remotion-core (board, eval, captions) ──┐     │            │
  └── mascot concepts ─[HUMAN pick]─ M4 ──────┤     │            │
                                              ▼     │            │
                M3 owner content ───────────► M5 Studio+Shorts ─ Gate B ─[HUMAN]─ freeze Nov 6
                (voices, line bank, games)    │     │
                                              ▼     ▼
                                   M6 Batch 0 ─ Gate C ─[HUMAN]
                                              ▼
                                   M7 first 5 uploads ─ Gate D ─[HUMAN]
                                              ▼
                                   M8 floor (65) ──► M9 target (+39)
```

## Milestones

| # | Milestone | Window | Depends on | Done when (spec section 13) | Gate / checkpoints |
| --- | --- | --- | --- | --- | --- |
| M1 | Day-1 risk tests | Oct 28 to 29 | Phase 0 | One API upload scheduled and confirmed not locked; OAuth app in production; TTS samples for 3 providers in EN and HI ready; one 60 s Remotion render timed on Actions | `[HUMAN]` Google Cloud OAuth client + consent screen set to "In production" + one-time consent click. `[HUMAN]` confirm before the real test upload, then check YouTube Studio shows Scheduled, not Locked. `[HUMAN]` ElevenLabs and Azure keys. |
| M2 | Contract + Python pipeline | Oct 28 to Nov 2 | Phase 0 contract; `voice` stage needs M1 `tts` adapters | Zod schema and JSON Schema exported (done in Phase 0); all Python stages emit valid specs for the 10 golden games | Gate A (auditors: agy + fresh Claude, since Codex builds M2). Triage in `audits/TRIAGE.md`. |
| M3 | Owner content prep | Oct 29 to Nov 4 | M1 TTS samples | `games.yaml` has 70+ approved games; line banks reviewed; voices chosen | `[HUMAN]` voice choice (EN, HI). `[HUMAN]` line bank review **by Nov 1**. `[HUMAN]` approve `games.yaml`. Claude drafts all three. |
| M4 | Mascot | Oct 28 to Nov 4 | concept sheets; remotion-core theme tokens | Owner picked a concept; 17 poses render in `MascotSheet`; 20 s reaction reel approved | `[HUMAN]` concept choice. `[HUMAN]` reel approval. Rig frozen after approval. |
| M5 | Studio + Shorts templates | Oct 30 to Nov 6 | remotion-core, M4 rig, M2 fixture specs | Gallery stills and a 60 s clip pass Impeccable audit and Gate B; owner approves; **features frozen Nov 6** | Gate B. `[HUMAN]` template approval from 6 stills + one 60 s clip. Also `[HUMAN]` palette: new Studio palette or existing `#161B26`/`#1E2533`. |
| M6 | Batch 0 | Nov 7 | M2, M3, M5 | One full EN and one full HI video rendered on Actions, watched end to end by the owner | Gate C. `[HUMAN]` sign-off on the first EN and HI videos. Render time from here sets the capacity plan. |
| M7 | First uploads | Nov 8 | M6, M1 upload test passed | 5 videos scheduled through the pipeline; ledger matches Studio | Gate D. `[HUMAN]` check the 5 in Studio. |
| M8 | Floor tier | Nov 8 to 11 | M7 | All 65 floor-tier uploads scheduled | Batches of about 20; owner reviews 1 in 5 contact sheets + all thumbnails. |
| M9 | Target tier | Nov 11 to 15 | M8 | As many of the remaining 39 as time allows, earliest dates first | Stops first if anything slips. |

## Workstreams running now (parallel worktrees)

Done and merged: `ws/m1-risk`, `ws/m2-pipeline`, `ws/remotion-core`, `ws/mascot-concepts` (plans `docs/superpowers/plans/2026-10-27-*.md`).

| Worktree / branch | Plan | Builder | Auditor |
| --- | --- | --- | --- |
| `.worktrees/m3-content` / `ws/m3-content` | `docs/superpowers/plans/2026-10-28-m3-content.md` | Sonnet subagent (PGN sourcing), Opus subagent (line banks), main session (game notes) | `line-checker` (Haiku) + tests; owner review |
| `.worktrees/m4-mascot` / `ws/m4-mascot` | `docs/superpowers/plans/2026-10-28-m4-mascot-rig.md` | Claude `remotion-builder` (Sonnet) | `design-critic` + Codex read-only or fresh Claude; owner reel approval |
| `.worktrees/m5-templates` / `ws/m5-templates` | `docs/superpowers/plans/2026-10-28-m5-templates.md` | Claude `remotion-builder` (Sonnet) | `design-critic`; Gate B: agy + fresh Claude; owner approval |

Oct 28: repo secrets set with `gh secret set` (`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`, `ELEVENLABS_API_KEY`). **No `ANTHROPIC_API_KEY`** (owner, Oct 28: none available; make as many videos as possible by the deadline). Scripts are written offline by agents (Claude subagents, Codex, agy) through the request/answer loop in `docs/offline-llm.md`, and final scripts are committed to `content/scripts/` and replayed on Actions. Script writing is now limited by agent usage, so the floor tier is scripted first. Day-1 upload confirmed Scheduled in Studio by the owner.

## If the schedule slips (spec section 13)

- Mascot late: ship with `idle` + reduced pose set (facepalm, slow_clap, shocked, party).
- Templates late: Gate B is the hard line on Nov 6. Past it, the floor tier renders with the legacy pipeline (`legacy/`) plus the new uploader.
- Rendering slow: stop the target tier, never the floor tier. Fallbacks: paid minutes, larger runners, Remotion Lambda.
- API uploads locked: submit the audit form the same day; owner schedules the floor tier by hand in Studio (3 to 4 h).

## Open owner decisions (spec section 14)

- [x] Mascot concept: **Pyaada** (owner, Oct 28). Sheets: `design/mascot/`, comparison https://claude.ai/artifact/5NQJVWXRBKch2WyHbuSYnD
- [x] TTS: **ElevenLabs Multilingual v2**, EN voice George `JBFqnCBsd6RMkjVDRZzb`, HI voice Sarah `EXAVITQu4vr4xnSDxMaL` (owner, Oct 28; samples https://claude.ai/artifact/QQZab3vhAVGzuNQKs6xJfn).
- [x] Repo visibility: **public** (`codewithpom/chesscode`). Consequence: logs reveal titles and games; MP4s never uploaded as artifacts; secrets only as repo secrets.
- [ ] Palette: new Studio palette or existing ChessCode colors.
- [ ] YouTube category: Gaming (default) or Education.
- [ ] `containsSyntheticMedia`: false (default) or true.
- [ ] End screens: skip, or add by hand to the first video of each series.
- [ ] Exact return date (confirms the 13-week window).
- [ ] Final `games.yaml` and reviewed line bank.

## Assumptions made where the spec is silent (raise to change)

1. `plies[].arrows[].color` is `best | threat | missed` (the spec's table row is truncated; `missed` serves the `missed_win` ghost arrow).
2. The spec gains `series` and `board: {orientation, theme}` (sections 5 and 6 need them; section 3 omits them). Themes: `bone_slate`, `walnut`, `cool_grey`, `warm_sand`.
3. `highlights[]` items are `{square, kind: last_move | check}`.
4. Player `rating`, `title`, `country` are required but nullable (historic games have none); `plies[].clock_ms` is nullable (classic games have no clocks).
5. `narration[].kind` is one of `cold_open, title, player_intro, ply, chapter, key_moment, verdict, outro`; `ply` is null for non-ply segments.
6. Assets are rendered with `--public-dir=<spec folder>` so `staticFile(audio)` resolves relative to the spec folder.
7. Third TTS bake-off provider is Kokoro (local, free, Hindi voices) because the owner has ElevenLabs and Azure keys only.
8. The 114 MB Windows Stockfish binary is not in the repo (GitHub limit); use `STOCKFISH_PATH` locally and apt `stockfish` on CI.
9. Codex builds; Codex-built work is audited by agy or a fresh Claude subagent (owner override of spec section 0).
10. Shorts get their own `video_id` because the schema pattern is `cc-<year>-<4 digits>-<lang>`: Short of game N uses game number N + 5000 (e.g. `cc-2026-5042-en`).
11. Beat pacing gaps (spec section 8 is silent): evals clamped to +/-10 pawns (mate = +/-10) before pawn-drop triggers; blunder/mistake beats also need the win% move class to agree; no beats on book plies except `opening_exit`; brilliant needs material given over reply + next move, and is suppressed at >= +5 unless the move is the engine's best; per-video caps `long_think 2, mistake 3, time_scramble 2`; full priority `checkmate > blunder > brilliant > missed_win > comeback > promotion > king_walk > time_scramble > resign > mistake > long_think > opening_exit`.
12. The uploader library keeps the spec 2 h `publishAt` guard; only the day-1 test script requires >= 3 h on its CLI argument.

13. Contract 1.1.0 (additive, from Gate A): `game.white/black.fact`, `cold_open {ply_from, ply_to, hook}`, `key_moments[] {beat_id, ply, start_ms, duration_ms, label, line}`, `verdict {turning_point_ply, accuracy}`, `thumbnail {text <= 4 words, ply, crop_origin, pose}`. All required; Python fills them in `emit`.

14. Pipeline choices under 1.1.0: cold open = `max(1, ply-2)..ply` of the top beat (priority, then intensity); key-moment `line` = first 8 UCI of `before[0].pv`; accuracy rounded to 2 decimals; thumbnail crop window is centred on the move (a move wider than 4 squares keeps its destination in view); a Short's script gets only its one beat as `short_beat`.
15. Calendar: spec section 11's alternating Friday short and Sunday target short could not sit 1 to 3 days before any long-form, so target games got one Short a week. `config/calendar.yaml` now has Fri EN (before Sat EN) and Sat HI (before Sun HI) target Shorts in their place.

## Owner decisions log

- Oct 28: mascot concept **Pyaada**.
- Oct 28: board pieces = rhosgfx (CC0) with black pieces recoloured to dark ink for contrast.
- Oct 28: Shorts layout deviates from spec section 6: board **864 px** (not 960) so captions, eval bar and board fit the upper 60 % and the mascot fits below.
- Oct 28: four series board themes get four distinct hue families (bone/slate, walnut, sage, a fourth muted hue) at the same square contrast.
- Oct 28: M1 render timing on Actions (public, 4 vCPU): 60 s Studio placeholder with real board, eval bar and captions rendered in about 50 s (run 40628324296); a 10-minute video is about 8 to 9 minutes. Re-measure at Batch 0 with full scenes.

## Tooling notes

- Codex here runs through a local compression proxy (`model_provider = "caveman"`), which can show function bodies as `...` with `<<ccr:...>>` markers. Codex prompts must say so and point at the `caveman_retrieve` MCP tool. Codex's first remotion-core audit ("no findings") may have read elided bodies; it is backed by tests plus two pixel-level design-critic passes, and Gate B will use agy and a fresh Claude auditor.
- The Codex sandbox cannot write the git index of a linked worktree, so the main session commits Codex's work with Codex co-authorship.
- Oct 28: OAuth: the legacy Chess Code token (consented Jul 14, still refreshing Oct 28, so the consent screen is "In production") passes `auth check` with both scopes. The secrets were copied to git-ignored `data/secrets/` with owner permission.
- Oct 28: Day-1 test upload `oriMknSnNT0` ("ChessCode API test (delete me)") is private, with publishAt 2026-10-29T04:43Z. **Owner to confirm in Studio that it shows Scheduled, not Locked**, then that it goes public, then delete it.
- Oct 28: The bake-off showed single-pass loudnorm missing spec (-15.7 LUFS, -0.46 dBTP). `audio.loudnorm` now uses iterative gain plus limiter (-14.5 LUFS, about -1.6 dBTP).
- Oct 28: Floor-tier Friday Short (spec section 11 conflict): the owner chose to keep it as a teaser for **next week's** long-form game. Friday still alternates EN/HI, so it teases next Tuesday's EN long-form (4 days ahead) or next Thursday's HI long-form (6 days ahead). The 1-3 day rule applies to every other Short. The floor tier keeps 39 Shorts.
- Oct 28: **M2 done, Gate A passed**: the agy and fresh-Claude audits both PASS, and the final round is verified (`audits/gateA*.md`, `audits/TRIAGE.md`). The pipeline emits video_spec 1.1.0; 280 Python and 64 Remotion tests pass.
- Status, Oct 28: **done**: M2, remotion core, mascot concept (Pyaada), voices, OAuth, Actions render timing, the day-1 upload; **owner check pending**: Studio shows `oriMknSnNT0` Scheduled, not Locked. **Next to plan**: M3 drafts (70+ `games.yaml`, line banks due Nov 1), M4 rig + 17 poses, M5 Studio/Shorts scenes.
