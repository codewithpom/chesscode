# Gate A3 audit (claude) - commits a36a9ec..28bfe12

pytest: 280 passed, 1 skipped (full `cd pipeline && python -m pytest -q`). Golden beats test passes; beats.yaml diff only removes the duplicate `poses:` block (values identical to the first one at line 5), so no golden regression.

## A2 fix rows
| Row | Status |
|---|---|
| M1 key moments 15-40 s, non-overlapping, Python mirror | verified-fixed. `emit.validate` (emit.py:177-180) matches Zod superRefine (schema.ts:276-284) rule for rule: 15000-40000 ms, `start < prev.start+prev.duration` = overlap, same messages. `key_moments()` sorts by start so the overlap rule is meaningful; narration is laid out sequentially so overlap cannot occur. Script gate (`key_moment_problems`, script.py) forces exactly one key_moment per intensity>=2 beat with 18-36 s of words (margin inside 15-40). Timeline beats are a subset of beats.json (pace never changes intensity), so no beat can need a missing segment. |
| M2 SAN guard bare squares + spelled-out moves | verified-fixed with limits (see findings). |
| Owner decision: Friday teaser (EN +4 d, HI +6 d, 39 Shorts) | verified-fixed. Scheduled 13 floor games: 65 uploads, 0 unassigned, 39 Shorts (13 teasers + 26), every teaser on a Friday, EN exactly +4 d, HI exactly +6 d, all other Shorts 1-3 d, no slot collisions. Week-1 teaser lands Fri 2026-11-13 (before `start`) by design. Ids game_no+6000 handled in runner (`%1000`), calendar `assign`, parse_video_id. |
| Teaser beat differs from other Shorts' beats | verified-fixed. `short_beat(teaser=True)` skips any beat within min_gap_ms/est_ms_per_ply (>=5 plies) of the top beat; script and timeline use the same function. |
| Minors: plies on one timestamp, chapter titles cut mid-word, poses defined twice, Hindi 8192 tokens | verified-fixed (piece_move_ms 280 spacing; `_title` cuts at word; poses deduped; script_hi 16384 + stop_reason==max_tokens raises). |
| Accuracy vs Lichess | deferred, not touched (correct). |

## Findings
severity | file:line | problem | fix
- minor | pipeline/chesscode/san_guard.py:154 | `_START_SQUARES` exempts every square on ranks 1,2,7,8 from the bare-square check, so "take on b7", "a8" etc. never flag (false negatives on 4 of 8 ranks). | Accept, or restrict exemption to squares a piece actually starts on plus engine/game squares; note in ROADMAP.
- minor | san_guard.py:152 | Spelled-out regex misses plurals/verbs ("rooks to e1", "knight jumps to f6") and Hindi oblique/variant spellings (e.g. "घोड़े", "रुक"). False negatives only. | Add variants if the LLM output shows them.
- minor | san_guard.py:19-35 | False positives: English "the knight on g5 attacks", "square h3 is weak" flag bare g5/h3 when no game/engine move lands there; Hindi place phrase "हाथी a1 पर है" flags as a move (Hindi has no "on" word to tell place from move). Each costs up to 3 regenerations, then StageError for the whole script. | Consider degrading to a warning for bare squares after attempt 2, or ignore a Hindi piece+square followed by "पर है".
- minor | stages/beats.py:200 + script.py:117 | A game with no beat >=5 plies from its top beat has no teaser and the Short stage hard-fails (StageError) rather than falling back. | Fall back to top_beat with a warning, or have calendar skip that teaser.
- minor | stages/timeline.py:~44 | Documented shortcut: plies after the last word start still share one timestamp. | Fine until a script covers far more plies than words.
- minor | stages/emit.py:178 | A key moment whose real TTS duration falls outside 15-40 s fails only at emit (after paid TTS). Margin is 3-4 s. | Optional: check voice duration at the voice stage.

No blockers, no majors.

READY TO MERGE
