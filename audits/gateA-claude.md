# Gate A audit (Claude, read-only) — ws/m2-pipeline

Auditor: fresh Claude subagent. I refreshed the graph (`graphify update .`, which rewrote graphify-out/ only) and ran graph queries before reading any source. I read SPEC sections 3, 4, 8, 11 and 12, the M2 plan, ROADMAP assumptions and TRIAGE.md. `pytest -q` gave 139 passed and 1 skipped (Windows, Python 3.12). Every claim below marked "verified" was reproduced with a small script.

## Findings (most severe first)

blocker | pipeline/chesscode/stages/timeline.py:22-28 | A ply gets a narration-aligned `show_at_ms` only if a `kind=ply` segment has exactly that ply. Every other ply gets `ply * est_ms_per_ply` (4500), which has nothing to do with the narration. The plan Task 8 range rule (a ply segment covers plies up to the next ply segment minus 1, at evenly spaced word starts) and the "before the first ply segment" rule are not implemented. Verified: with ply segments for plies 1 and 20, the result is ply1=30300, ply2=9000, ply5=22500 (during the cold open), ply19=85500, ply20=60600. So times go backwards, moves appear during the cold open, and moves land mid-word. Beat `at_ms` (line 29) inherits the same wrong times. | Implement the range rule as specified: compute show times per covered range from that segment's word starts, clamp plies before the first ply segment to its start, then assert the times are monotonic and on word starts. Add a test with sparse ply segments.

blocker | pipeline/tests/test_e2e.py:61-75 | The end-to-end "40 specs validate" test masks the problem above. The fake script has one `cold_open` segment and no `ply` segments, so every ply in all 40 specs is on the 4500 ms fallback. `ensure_specific` is also monkeypatched out. | Make the fake script emit ply segments for a subset of plies. Assert that `show_at_ms` is monotonic, falls on a word start and is at or after its segment start.

blocker | pipeline/chesscode/stages/script.py:81-87 (and 55-75) | SAN guard bypass. The guard checks only `segments[].text`, and it runs before the specificity regeneration (line 81) and the length regeneration (line 85). Both of those replace the whole output with a new LLM response that is never SAN-checked. `mascot_lines`, `titles` and `hook` are never checked at all; the hook goes into the YouTube description and titles go to YouTube. | Run the guard (with targeted regeneration) as the last step, over the final output including titles, hook and mascot lines.

blocker | pipeline/chesscode/stages/timeline.py:30 | The re-pace passes `cfg.get("beats", cfg)`, but `config/timeline.yaml` has no `beats` key, priority, poses, alt_poses or max_per_type. In the real run, pace therefore uses silent default gaps and an empty priority list, so it orders by intensity. That breaks review focus 5 ("priority wins, not intensity") once real ms are known. `test_timeline.py` hides this by passing a `cfg["beats"]` that the real run never provides. | Load `config/beats.yaml` in timeline, add it to timeline INPUTS, and drop the `.get(..., default)` fallbacks.

major | pipeline/chesscode/stages/timeline.py:56 | The Shorts beat is chosen with `max(priority, ...)`. But `priority` is the index into the priority list (0 = checkmate), so this picks the least important beat. For example, the Opera Game Short would be built on `opening_exit` instead of `checkmate`. The e2e test only asserts `len(beats)==1`. | Use `min` on priority, then the highest intensity. The script stage should also be told which single beat the Short is about.

major | pipeline/chesscode/stages/emit.py:13,42 | Pose comes from a hard-coded `_POSES[kind]`, which discards the `pose` computed in beats.py. That pose carries the intensity-3 blunder `faint` and the alternate pose used to avoid "same pose twice in a row". So the spec never contains `faint`, and the no-repeat rule can be broken. `_FX` is also duplicated between beats.py and emit.py. | Use `b["pose"]`. Re-check no repeated pose at emit.

major | pipeline/chesscode/stages/emit.py:25-35,43 | Silent defaults, against spec section 3: player name "Unknown", "Unknown event", date "????-??-??", ECO "A00", "Unknown opening", result default "1/2-1/2", class "best", `best_uci` set to the played move, `show_at_ms` 0, intensity 1, eval `{cp:None, mate:None}`. The music track `music/bed_calm_01.mp3` is hard-coded and never copied into the spec folder, so it will not resolve under `--public-dir=<spec folder>`. Result "*" silently gives a black orientation. | Raise StageError on any missing value. Take music from config and copy it into the folder (or check it exists).

major | pipeline/chesscode/stages/emit.py:48 | `FormatChecker()` without `rfc3339-validator` installed does not check `date-time`. Verified: `'date-time' in FormatChecker().checkers` is False here. So `youtube.publish_at` is not format-validated in Python, while Zod `z.iso.datetime()` (Z only, no offsets) would reject a bad value. Python validation is weaker than the contract. | Add `jsonschema[format-nongpl]` or `rfc3339-validator` to dependencies, and a test that a bad `publish_at` fails. Also mirror Zod's Z-only rule.

major | pipeline/chesscode/stages/beats.py:40-42 | The blunder trigger and intensity do not match the spec section 8 table. Class `blunder` alone fires a blunder beat even when the pawn drop is under 2.0, which the table calls a mistake. `3 if cls=="blunder"` forces intensity 3 for every class blunder, so the drop ladder (4.0 → 3, 3.0 → 2) is dead code. All 7 golden blunders are intensity 3 / `faint`, and that also widens the 60 s intensity-3 gap. ROADMAP assumption 11 does not cover this. | Require drop ≥ blunder_drop (or winning → ≤ 0) and apply the intensity ladder. Record any deliberate deviation as an assumption.

major | config/beats.yaml priority + beats.py:68-89 | `resign` ranks below `time_scramble`, and the final-ply beat can be dropped by pacing. In 2 of the 10 golden decisive games (gukesh-ding-wch2024-g3 1-0, pragg-gukesh-cand2024-r2 0-1) a time_scramble 1 to 4 plies earlier removes the `resign` beat, so the video has no ending beat or outro sting. | Never drop the final checkmate/resign beat. Drop the competing beat instead.

major | pipeline/chesscode/stages/beats.py:68 (pace) | The section 8 rule of 8 to 14 beats per 10 min (scaled by length; Shorts 2 to 4) is not enforced or checked anywhere. Golden output is 2 to 8 beats per game (Opera 2, Ding–Gukesh g14 4) for 8 to 12 minute videos. | At least check and fail (or warn into qa.json) on counts out of range; consider scaling by actual duration in timeline.

major | pipeline/chesscode/calendar.py:116-122 | (a) The series interleave silently drops games when series are unbalanced. Verified: 5 floor games (4 legendary, 1 opening) produce only 4 scheduled games. (b) The rule "no series more than 2 long-form weeks in a row" is never checked; one dominant series runs back to back. (c) The target tier can never be scheduled. Slots are filtered to `tier==target`, and the only target short slot (Sunday) is never 1 to 3 days before Saturday's long-form, so it always raises "no target short slot". Verified. (d) Floor and target are assigned in separate calls with separate `occupied` sets, so cross-tier same-time checks would be missing once (c) is fixed. | Schedule both tiers in one pass over all slots. Fix the round-robin to drain all queues, validate the series rule, and add tests for unbalanced series and the target tier.

major | pipeline/chesscode/san_guard.py:5 | Regex gaps. Bypasses: `0-0-0` / `0-0` (zeros), `e8Q` (promotion without "="), long algebraic forms, and piece names written in words or Devanagari. False rejects: `O-O+` is extracted as `O-O` (game SAN is `O-O+`); `Qxf7` written without the `#` that the game SAN has; and bare squares ("the e5 square") are extracted as pawn moves. The false rejects lead to regeneration loops and then a StageError. | Normalize both sides (strip `+#`, map 0→O, accept `e8Q`/`e8(Q)`). Treat a bare `[a-h][1-8]` as a move only when it is a legal pawn move that is not in the game. Add the Hindi, castling and promotion cases as tests.

major | pipeline/chesscode/stages/script.py:12,88-110 | Idempotency and hashing. (a) `prompts/script_system.md` in INPUTS is resolved against spec_dir by `runner._input_hash`, so it always hashes as `<missing>` and prompt edits never re-run the script stage. (b) `line_history` is appended on every run, including reruns and runs where a later stage fails. On rerun the video's own previous lines count as "recent", so the output changes and bank lines get used up. | Hash the prompt by its package path. Write line_history once per video_id (delete then insert), and exclude the current video_id from "recent".

major | .github/workflows/ (only timing.yml) | No workflow runs `pytest` (spec section 12: "run in ci.yml"), so nothing has been verified on Ubuntu. | Add ci.yml: Ubuntu, Python 3.12, `pip install -e pipeline[dev]`, pytest (engine tests skipped).

major | pipeline/chesscode/stages/script.py:47 | The Hindi prompt is the English prompt plus "Do not translate or use any English script". That contradicts joke rule 3 (keep fork, pin and blunder in English) and conflicts with SAN tokens in Latin script. This is not the "Hindi-native prompt" the plan asks for. | Write a separate Hindi system prompt that states the register explicitly.

minor | pipeline/chesscode/stages/timeline.py:33-44 | Chapter titles are narration text cut at 70 characters mid-word. "Opening"@0 is inserted even when the next chapter starts under 10 s later, which breaks YouTube's 10 s chapter rule. Filler "Chapter N" entries are added at arbitrary 10 s marks, and Shorts get 3 filler chapters. | Use script-provided chapter titles, enforce spacing after the insert, and skip chapters for Shorts.

minor | pipeline/chesscode/stages/timeline.py:13,19 | The reaction gap uses beats from before the re-pace, and only when the segment ply exactly equals the beat ply (not "the segment that contains the beat"). | Compute it after the re-pace, using coverage ranges.

minor | pipeline/chesscode/stages/analyze.py:53 + classify.py:87,131 | `after=None` on the final ply of every game, not only on terminal positions. A last-move blunder before resignation is classified with loss 0, and the final ply's `eval` is the eval before the move (for example M1 instead of mate). | Analyse the final position unless `board.is_game_over()`.

minor | pipeline/chesscode/stages/metadata.py:103 | The title "scorer" is `valid[0]`; there is no Haiku scoring (spec section 11). | Wire the `checks` model.

minor | pipeline/chesscode/calendar.py:115, llm.py:125 | `load(...)` uses the module REPO_ROOT, not `ctx.repo_root`. | Pass the root through.

minor | pipeline/chesscode/runner.py:34, calendar.py:125 | `game.get("year", year)` and `game.get("year", start.year)` are silent defaults. | Make `year` required in games.yaml, or derive it once.

minor | pipeline/chesscode/stages/emit.py:10 | An absolute schema path in INPUTS goes into the hash, so stage hashes differ per machine or worktree. emit INPUTS also omit game.pgn, and voice INPUTS omit the audio files (deleted mp3s are not detected). | Use repo-relative names and check that audio outputs exist.

minor | pipeline/chesscode/stages/classify.py:101 | `missed_win` ignores mate scores, so a missed forced mate is never `missed_win`. | Treat a mate for the mover as ≥ best_min_pawns.

minor | pipeline/chesscode/llm.py:134 | Transient API errors are not retried (only invalid JSON is). | Retry with backoff on 429, 5xx and connection errors.

## Checklist answers

1. **Is the schema complete for every scene?** Mostly. ColdOpen, TitleCard, PlayerIntro, Playback (ply), KeyMoment, Verdict and Outro map to `narration[].kind`. Remotion needs these things the spec cannot carry, or that emit never fills:
   - The outro start or length. It is implicit (`duration_ms − 20000`, and 0 for Shorts), so Remotion must hard-code a per-template constant.
   - Title-card and thumbnail text, and the thumbnail's key ply.
   - An engine variation (PV) for KeyMoment replays. Only `best_uci` exists.
   - Arrows. Emit always writes `[]`, so the missed_win ghost arrow and best arrows are missing.
   - Check highlights. Emit never emits `check`.
   - `sfx`, which is always null.
   - A music asset in the spec folder; the path is hard-coded.
   - For Shorts: the focus beat or ply, and the linked long-form video id. Shorts also carry every ply of the game on synthetic timings.

2. **Can timing overlap audio, show a move mid-word, or go backwards?** Narration cannot overlap: segments are laid out sequentially, and emit and Zod both check. Moves can go backwards and land mid-word: yes, see the timeline.py:22-28 blocker (verified). Only plies that have their own `ply` segment are placed on a word start; every other ply uses `ply × 4500 ms`. Beats inherit these times, and the re-pace ignores priority.

3. **Do beat thresholds match the 10 golden games?** The golden expectations match the code, and the test passes. They do not fully match spec section 8:
   - Every class blunder is forced to intensity 3.
   - A class blunder fires a beat without the 2.0 drop.
   - 2 decisive games lose their final `resign` beat.
   - Beat counts are 2 to 8 per game against the required 8 to 14.

   Triggers never exercised on golden data: `comeback`, underpromotion (intensity 3), blunder intensity 1 and 2, and `long_think` by the ≥ 300000 ms rule (as opposed to the fraction rule). `missed_win` and `king_walk` fire only once each.

Other checks:
- Secrets: no key or token is logged; the ElevenLabs and Azure errors strip details.
- Spec section 11 calendar rules: see the calendar.py finding.
- Emit cross-field mirror: matches Zod `superRefine` (Python adds Shorts ≤ 59000 and exactly one beat) except for the `date-time` format gap.
- Ubuntu CI: untested (no workflow).

**Verdict: FAIL** — 4 blockers (ply timing not narration-aligned and non-monotonic, an e2e test that masks it, a SAN-guard bypass through regeneration and unchecked fields, and timeline re-pace ignoring priority) plus 12 majors.
