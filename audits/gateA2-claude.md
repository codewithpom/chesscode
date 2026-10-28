# Gate A re-audit (Claude, read-only): ws/m2-pipeline @ 03b5734

Auditor: a new Claude subagent. Before reading any source I ran `graphify update .` (no topology change) and the graph queries. Then I re-checked every finding in gateA-claude.md and gateA-agy.md against the "| A |" rows in TRIAGE.md, and reviewed the contract 1.1.0 additions.

Commands run, none of which changed the repo:
- `pytest -q` gave **234 passed, 1 skipped** (Windows, Python 3.12). basetemp was in the scratchpad.
- **All 40 e2e-generated specs passed the real Zod `VideoSpec`** (`remotion/src/spec/schema.ts` from this worktree, zod 4.5.4, run with tsx from the scratchpad): ok=40, bad=0.
- `npm run check-schema` (export-schema `--check`) passed, and the tree was still clean afterwards.

## Status of previous findings

| Finding | Status | Evidence |
| --- | --- | --- |
| B1 timeline ply coverage (agy B1 / claude B1) | verified-fixed | timeline.py:10-37 implements `_coverage` and `_show_at` per Task 8. In all 40 e2e specs, show_at_ms never decreases and always falls on a word or segment start. |
| B2 e2e masks timing | verified-fixed | test_e2e.py:64-70 uses sparse ply segments; :108-115 asserts monotonic times, word starts, first ply at the first ply segment, and beat at_ms equal to the ply's time. |
| B3 SAN guard order and coverage | verified-fixed | script.py:133-139 runs the guard last, over segments, titles, hook, cold_open_hook, thumbnail_text, player_facts and key_moment_labels. Mascot lines are checked at :151 and :156. (The regex gap is reported below.) |
| B4 re-pace without beats.yaml | verified-fixed | timeline.py:7 and :73 load beats.yaml and add it to INPUTS; there is no `.get` fallback. |
| Shorts used `max` on priority | verified-fixed | beats.py:70-72 `top_beat` uses min priority, then highest intensity, then earliest ply. script.py:111 and timeline.py:76 use the same function. |
| emit hard-coded poses | verified-fixed | emit.py:141 uses `b["pose"]`; the repeat check is at emit.py:168-170. |
| emit silent defaults, arrows, check, sfx, music (agy + claude) | verified-fixed | emit.py:30-34 `_need`; :36-46 arrows and check highlight; :135/:141 sfx; :65-78 music copied or placeholder plus a `.placeholder` QA marker. |
| publish_at format not checked | verified-fixed | emit.py:26 and :156-160, with a test at test_emit_assemble.py:139. |
| Class blunder always intensity 3 | verified-fixed | beats.py:42-44: drop ladder plus the agreeing-class rule. Golden expectations re-pinned (run 3). |
| Final resign beat lost to time_scramble | verified-fixed | beats.py:79-95: FINAL is never dropped. Every decisive long-form e2e spec ends on checkmate or resign. |
| Calendar crash, dropped games, series rule (agy B2 / claude) | verified-fixed | calendar.py:21-58: one pass, `occupied` shared across tiers, overflow goes to `unassigned` with a reason, `_order` caps a series at 2 in a row. The calendar.yaml change is recorded as ROADMAP assumption 15. |
| SAN regex: 0-0, e8Q, suffixes, bare squares | **partly fixed** | san_guard.py:112-120 handles castling with zeros, promotion without `=`, and `+#` suffixes. Bare squares are now skipped entirely (:124 shortcut). See major M2. |
| Prompt not hashed; non-portable hash names; line_history | verified-fixed | runner.py:46-50 resolves `pipeline/...` and `spec/...` against the repo root and hashes POSIX names; script.py:14 hashes the prompt by its repo path; script.py:53 and :162 exclude this video's own lines and replace them on rerun. |
| No CI | verified-fixed | .github/workflows/ci.yml runs pytest on Ubuntu 24.04 with Python 3.12, plus tsc, vitest and check-schema. |
| Hindi prompt | verified-fixed | script.py:27 HINDI_ADDENDUM (chess terms in English, SAN in Latin script). |
| Contract lacks scene data (agy checklist 1) | verified-fixed | contract 1.1.0 fields are emitted at emit.py:145-148. |
| Title scorer, credits, duplicated chapters (agy) | verified-fixed | metadata.py:37-46 and :56; emit.py:148 strips `chapters` from `youtube`. |
| Regeneration IndexError (agy) | verified-fixed | script.py:73-78. |
| Missing line bank crash (agy) | verified-fixed (bank deferred) | script.py:98-101 raises a clear StageError. content/lines/ is still empty, so any rejected mascot line stops the run. |
| Shorts chapter crash (agy) | verified-fixed | timeline.py:77 sets min_chapters to 0 for Shorts. |
| Emit stricter than Zod (agy) | rejected in triage; still as triaged | emit.py:161-164. |
| 8-14 beats; comeback unexercised | deferred in triage | Unchanged. |
| Claude minors (not triaged) | still open | Chapter titles cut mid-word (timeline.py:53); `year` default (runner.py:33, calendar.py:38); voice INPUTS omit audio (voice.py:12); missed_win ignores mate (classify.py:101); final ply `after=None` (analyze.py:53). |

## Python mirror of the Zod superRefine (emit.validate, emit.py:150-182)

Each superRefine rule has a Python equivalent:

| Zod rule | Python check |
| --- | --- |
| video_id = pair_id-language | :154-155 |
| Shorts 1080x1920 | :162 (stricter: also fps 30) |
| Shorts duration | :163 (stricter: 59000 ms instead of 175000, as triaged) |
| Narration does not overlap | :166-167 (same comparison) |
| cold_open is a forward range of existing plies | :173-174 |
| key_moment ply exists and beat_id references a beat | :175-177 |
| verdict.turning_point_ply exists | :178 |
| thumbnail.ply exists | :180 |
| thumbnail.text is not the title (case-insensitive) | :181 |
| plies numbered 1..n | :171 |

Python also checks things Zod does not: publish_at must be ISO UTC ending in Z, no repeated pose, and exactly one beat per Short. No Zod rule is missing in Python, and the Python checks never accept something Zod rejects. Neither side checks that key moments do not overlap (see M1).

## New 1.1.0 fields

- **facts**: required by `_need`, at most 120 characters (script SCHEMA :19), and SAN-guarded. OK.
- **cold_open**: plies `top-2..top` with the hook (60 characters max). OK. Remotion must draw the position before `ply_from`.
- **verdict**:
  - The per-move formula at emit.py:97 is exactly `103.1668*exp(-0.04354*loss)-3.1669`, clamped to 0..100.
  - The loss sign is correct for each side: the analysis is from White's point of view (analyze.py:28), odd plies are White's moves, and `before[0]` is the best line before the move.
  - The turning point is the largest win% swing toward the winner, or the largest absolute swing in a draw. Correct.
  - Gap against Lichess (minor m3): Lichess adds a +1 bonus to each move's score and averages the moves with a volatility-weighted mean combined with a harmonic mean, not a plain mean.
- **key_moments**: see M1.
- **thumbnail crop**:
  - `crop_origin` (emit.py:80-87) always returns a square within a1..e5.
  - It contains both squares whenever the move spans 4 or fewer files and 4 or fewer ranks; otherwise it keeps the destination square.
  - Verified on the e2e specs: d1d8 → c5 (destination only, as documented); a8b7 → a5 (both squares).

## Findings (most severe first)

major | pipeline/chesscode/stages/emit.py:101-112 (+ prompts/script_system.md:18,25) | **M1.** When a beat has no `key_moment` narration segment, the KeyMoment takes its window from the whole covering `ply` segment. Several beats in one segment then get the same window. Verified: in cc-2026-0006-en/hi, b-03 (blunder) and b-04 (resign) have identical start_ms and duration_ms. That window is also the Playback window, so moves animate during the replay. Nothing checks the spec section 5 length of 15-40 s or non-overlap, and Zod accepts the spec. The prompt contradicts itself: line 18 says key_moment segments have "ply null", line 25 says they carry the beat's ply. So a real LLM run will often hit this fallback. | Require one `key_moment` segment (with the beat's ply) for each KeyMoment beat in script.py, next to the label check at :141-143, and drop the fallback. Fix prompt line 18. Add a non-overlap and 15-40 s check to both emit.validate and the Zod superRefine.

major | pipeline/chesscode/san_guard.py:124 | **M2.** The bare-square shortcut turns the old false-reject into a bypass. Any invented pawn move written bare ("Black played d5" when the game had ...d6) is never checked. The same applies to piece moves spelled out in words, Latin or Devanagari ("नाइट f3", "knight to f6"), and to `e2-e4`. Pawn moves are a large share of the moves a narrator names. TRIAGE asked for a fix; this is a shortcut. | Treat a bare square as a move when a legal pawn move to it exists in a position of the game (or the engine lines) and it is not one of the game or engine moves. Add Hindi and English pawn-move tests.

minor | pipeline/chesscode/stages/timeline.py:36 | When a segment covers more plies than it has words, several plies share one show_at_ms, so the board jumps several moves on one frame. Verified in e2e Shorts: up to 58 plies share timestamps in cc-2026-5008-hi. A Short still carries the whole game after its beat. | Raise (or warn into qa) when covered plies exceed words; for Shorts, limit plies to the beat window.

minor | pipeline/chesscode/stages/emit.py:97-99 | Accuracy is "Lichess-style" but has no +1 bonus per move and uses a plain mean. The final ply always scores 100 because `after=None` (analyze.py:53). | Either match Lichess (bonus, plus weighted and harmonic means) or call it an approximation; analyse the final position unless the game is over.

minor | pipeline/chesscode/stages/timeline.py:53,61-64 | Chapter titles are narration text cut at 70 characters mid-word. When fewer than 3 chapter segments exist, filler "Chapter 2" and "Chapter 3" are added at 0:10 and 0:20, during the cold open. All 20 e2e long-forms got these fillers. | Take chapter titles from the script, and place fillers at real segment boundaries.

minor | config/beats.yaml:5,55 | The `poses:` key appears twice. PyYAML keeps the last one silently, so an edit to the first block has no effect. | Delete one block.

minor | pipeline/chesscode/llm.py:8-31 | `max_tokens=8192` with no check of stop_reason, and no stripping of code fences around the JSON. A Hindi long-form script (up to about 1680 Devanagari words plus the JSON fields) risks truncation, which shows up only as "invalid model JSON". | Check `stop_reason`, raise max_tokens or use structured output, and strip code fences.

minor | runner.py:33, calendar.py:38, voice.py:12, classify.py:101 | Claude minors that were never triaged are still open: the `year` default, voice INPUTS without the audio files, and missed_win ignoring mate scores. | Triage them.

## Checklist answers

1. **Is the schema complete for every scene?** Yes for data, with 1.1.0:
   - ColdOpen: `cold_open`.
   - TitleCard: `game`.
   - PlayerIntro: `fact`.
   - Playback: `plies` and `narration`.
   - KeyMoment: `key_moments` with `line`.
   - Verdict: `verdict`.
   - Outro: implied by `duration_ms − outro`.
   - Shorts: one beat plus `cold_open`.

   What the spec still cannot carry for Remotion:
   - A KeyMoment window that does not overlap Playback (M1).
   - The outro start (still implicit).
   - The Shorts ply window (the whole game is carried).
   - The thumbnail when the board orientation is black (crop_origin is from White's view, so Remotion must mirror it).

2. **Can timing overlap audio, show a move mid-word, or go backwards?**
   - Audio cannot overlap.
   - A move is never shown mid-word.
   - Times never go backwards (verified on 40 specs).
   - Remaining issue: several plies can share one timestamp (minor).

3. **Do the beat thresholds match the 10 golden games?** Yes: the re-pinned golden beats pass 10/10, and the blunder ladder, the agreeing-class rule and the never-dropped final beat are in place. `comeback`, underpromotion and the `long_think` 300 s rule are still not exercised by golden data (deferred).

**Verdict: PASS.** No blockers; 2 majors (M1, M2) should be fixed before Gate B renders KeyMoment scenes.
