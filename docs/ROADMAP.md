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

| Worktree / branch | Plan | Builder | Auditor (never the builder's own vendor for Codex work) |
| --- | --- | --- | --- |
| `.worktrees/m1-risk` / `ws/m1-risk` | `docs/superpowers/plans/2026-10-27-m1-risk-tests.md` | Codex (`codex exec -s workspace-write`) | fresh Claude subagent |
| `.worktrees/m2-pipeline` / `ws/m2-pipeline` | `docs/superpowers/plans/2026-10-27-m2-pipeline.md` | Codex | agy + fresh Claude (Gate A) |
| `.worktrees/remotion-core` / `ws/remotion-core` | `docs/superpowers/plans/2026-10-27-remotion-core.md` | Claude `remotion-builder` (Sonnet) | Codex read-only + `design-critic` |
| `.worktrees/mascot-concepts` / `ws/mascot-concepts` | `docs/superpowers/plans/2026-10-27-mascot-concepts.md` | Claude main session (design judgment) | fresh Claude `design-critic` |

Next to plan (after these land): M3 drafts (`games.yaml`, line banks), M4 rig, M5 scenes, `qa`, `upload` full, `batch.yml`/`collect.yml`.

## If the schedule slips (spec section 13)

- Mascot late: ship with `idle` + reduced pose set (facepalm, slow_clap, shocked, party).
- Templates late: Gate B is the hard line on Nov 6. Past it, the floor tier renders with the legacy pipeline (`legacy/`) plus the new uploader.
- Rendering slow: stop the target tier, never the floor tier. Fallbacks: paid minutes, larger runners, Remotion Lambda.
- API uploads locked: submit the audit form the same day; owner schedules the floor tier by hand in Studio (3 to 4 h).

## Open owner decisions (spec section 14)

- [x] Mascot concept: **Pyaada** (owner, Oct 28). Sheets: `design/mascot/`, comparison https://claude.ai/artifact/5NQJVWXRBKch2WyHbuSYnD
- [ ] TTS provider and voices for EN and HI, after the bake-off.
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
