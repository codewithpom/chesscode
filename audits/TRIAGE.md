# Audit triage

One row per auditor finding: fix, defer or reject, with a one-line reason.

| Gate | Source | Finding | Decision | Reason |
| --- | --- | --- | --- | --- |
| A-pre | m1-a-claude | auth.py token/client_secret paths relative to cwd; pipeline/data/secrets not ignored | fix | Public repo: refresh token could be committed. .gitignore hardened on main now; path anchoring sent to Codex. |
| A-pre | m1-a-claude | azure.py duration is timedelta; empty word list cached | fix | Breaks Azure bake-off silently. |
| A-pre | m1-a-claude | align.py is ASR not forced alignment; KeyError on numbers | fix | Captions must match script words. |
| A-pre | m1-a-claude | elevenlabs.py prefers normalized_alignment | fix | Caption words must match script. |
| A-pre | m1-a-claude | upload.py retries without uploads-playlist check; no upload_log.csv | fix (playlist check) / defer (csv) | Spec section 10 idempotency; ledger CSV belongs to M7 uploader. |
| A-pre | m1-a-claude | test_auth no-token-leak test vacuous; refresh path untested | fix | Secret-leak tests must bite. |
| A-pre | m1-a-claude | auth errors give stack traces | fix | Actionable messages. |
| A-pre | m1-a-claude | publishAt microseconds; containsSyntheticMedia unset; title/description lengths | fix | Spec section 10. |
| A-pre | m1-a-claude | transport errors not retried; missing retry tests | fix | Robust uploads. |
| A-pre | m1-a-claude | ElevenLabs error drops status; 10K char limit | fix | Diagnosability; long scripts. |
| A-pre | m1-a-claude | cache key lacks lang/model; raw output discarded before loudnorm; mp3 re-encode delay | fix (keep raw) / defer (key) | Spec fixes key as (provider, voice, text); voice id already implies language. Encoder delay measured at bake-off. |
| A-pre | m1-a-claude | Hindi fixture doubled nukta | fix | Test must use plan string. |
| A-pre | m1-a-claude | day1 dry-run prints hand-built body, skips guard | fix | Dry run must show the real request. |
| A-pre | golden-review-claude | `_material_given` uses full PV | fix | 15 false brilliants per game; Qb8+ missed. |
| A-pre | golden-review-claude | brilliant in decided positions | fix | Adds best<+5 or played==best rule (spec gap). |
| A-pre | golden-review-claude | mate scores give infinite drops | fix | Clamp to +/-10 pawns. |
| A-pre | golden-review-claude | pawn-drop beats contradict win% class | fix | Beat requires agreeing class (spec gap, assumption recorded). |
| A-pre | golden-review-claude | beats on book plies | fix | Only opening_exit during book. |
| A-pre | golden-review-claude | no pose in beats.json | fix | Spec section 8 table. |
| A-pre | golden-review-claude | checkmate/resign intensity 1 | fix | Comic timing needs >= 2. |
| A-pre | golden-review-claude | unordered "rest" priority | fix | Explicit order recorded as assumption. |
| A-pre | remotion-core-codex | no findings | n/a | Design review pending (design-critic). |
| A-pre | design-critic (remotion-core, 2 passes) | 10 visual fixes (coords, last-move tint, check stroke, eval bar, blunder contrast, Hindi stress text, caption size) + 3 owner items | fix | All verified in pixels on pass 2; owner decided piece recolour, 864 Shorts board, four hues. |
| A-pre | design-critic pass 2 | SPEC.md section 6 still says #E5484D, red glow, 960 board | defer | SPEC is the owner's document; deviations are logged in docs/ROADMAP.md decisions; owner may update SPEC. |
| A-pre | design-critic pass 2 | theme keys cool_grey/warm_sand now sage/rose | defer | Schema change; rename at next contract bump (needs Python + Zod together). |
| A-pre | design-critic pass 2 | vertical eval label overlaps a8 corner area | defer | M5 scene layout task. |
| A-pre | remotion-core-codex-2 | CoreGallery local msF | fix | Now wraps msToFrame. |
| A-pre | remotion-core-codex-2 | Task 6 review not recorded | fix | Recorded in these rows. |
| A | gateA-agy B1 / gateA-claude B1 | timeline: plies outside an exact ply segment fall back to n*4500 (backwards, mid-word) | fix | Plan Task 8 coverage rule was never implemented. |
| A | gateA-claude B2 | e2e fake script has no ply segments, hides B1 | fix | e2e must use ply segments and assert monotonic, word-start show_at_ms. |
| A | gateA-claude B3 | SAN guard runs before rewrites; mascot lines/titles/hook unchecked | fix | Guard every final text. |
| A | gateA-claude B4 | timeline re-pacing reads timeline.yaml without priority/poses/caps | fix | Must reuse config/beats.yaml. |
| A | gateA-agy B2 / gateA-claude | calendar crashes on target tier, crashes past floor capacity, drops games, series rule unchecked | fix | Leave overflow unassigned with a reason; never crash; enforce section 11. |
| A | gateA-claude | shorts pick least important beat (max on priority index) | fix | |
| A | gateA-claude | emit hard-codes poses (faint/alt lost) | fix | |
| A | gateA-agy / gateA-claude | emit silent defaults; arrows always []; no check highlights; sfx None; music path hard-coded, file not copied | fix | Spec section 3 no silent defaults. Music: config/music.yaml + copied file; generated silent bed placeholder until licensed music exists (flagged in QA). |
| A | gateA-claude | publish_at never format-checked (format lib missing) | fix | Explicit ISO-8601 UTC check. |
| A | gateA-claude | class-blunder always intensity 3 | fix | Intensity from drop per section 8; golden expectations re-reviewed. |
| A | gateA-claude | final resign beat lost to time_scramble | fix | Final-ply beat (checkmate/resign) is never dropped. |
| A | gateA-claude | 8-14 beats per 10 min not enforced | defer | Pacing can only drop beats; minimum becomes a QA warning at Gate C. |
| A | gateA-agy / gateA-claude | SAN regex: 0-0, e8Q, suffixes, bare squares | fix | |
| A | gateA-agy / gateA-claude | script prompt not hashed; non-portable hash names; line_history polluted on rerun | fix | Idempotency. |
| A | gateA-claude | no CI workflow runs pytest | fix | Add ci.yml per spec section 9 (pytest, tsc, vitest, schema check). |
| A | gateA-claude | Hindi prompt "no English script" contradicts joke rule 3 | fix | Means "not translated from the English script"; chess terms stay English. |
| A | gateA-agy checklist 1 | contract lacks cold-open ply range, player facts, key-moment lines, verdict turning point/accuracy, thumbnail text/crop | fix (main session) | Additive contract 1.1.0 designed by main session, then pipeline fills it. |
| A | gateA-agy | emit stricter than Zod (shorts 59 s, one beat, fps 30) | reject | Intentional: plan sets Shorts default <= 59 s and one beat; Zod keeps the spec hard limits. |
| A | gateA-agy | title scorer hard-coded valid[0]; credits empty; chapters duplicated in youtube | fix | |
| A | gateA-agy | script regeneration IndexError when one segment returned | fix | |
| A | gateA-agy | line bank files missing, rejection crashes | fix (clear StageError) / defer (bank) | Bank is M3 owner content; drafted next. |
| A | gateA-agy | shorts chapter generation crashes | fix | |
| A | gateA-agy | comeback trigger unexercised by golden games | defer | Covered by unit test; add a golden comeback game in M3 games list. |
| A2 | gateA2-agy | all prior findings verified fixed; checklist answered | n/a | Verdict PASS. |
| A2 | gateA2-claude | all prior blockers fixed; 40 e2e specs pass real Zod | n/a | Verdict PASS with 2 majors below. |
| A2 | gateA2-claude M1 | key moments share one move window; prompt contradicts itself on key-moment ply | fix | Script must emit one key_moment segment per intensity>=2 beat (15-40 s); Zod rule added on main (ce7d9ca); Python mirror. |
| A2 | gateA2-claude M2 | bare squares / spelled-out moves skip the SAN guard | fix | Check bare destination squares against game + engine-line destinations; flag spelled-out piece moves ("knight to f6", Hindi piece names + square) the same way. |
| A2 | owner decision | Friday floor Short teases next week's long-form (EN +4 d, HI +6 d) | fix | ROADMAP decisions log, Oct 28. |
| A2 | gateA2-claude minors | several plies on one timestamp; chapter titles cut mid-word; poses defined twice in beats.yaml; Hindi script may hit 8192 output tokens | fix | Cheap and user-visible. |
| A2 | gateA2-claude minor | accuracy differs slightly from Lichess (no volatility weighting) | defer | Display-only; revisit if viewers compare with Lichess. |
| A3 | gateA3-claude | all A2 fix rows verified; floor = 39 Shorts, teasers EN +4 d / HI +6 d | n/a | READY TO MERGE. |
| A3 | gateA3-claude minor | SAN guard: ranks 1/2/7/8 squares unchecked; some phrasings slip; "knight on g5 attacks" / "हाथी a1 पर है" falsely flagged | defer | Measure on real scripts at Batch 0 (M6); tune with the Gate C chess check. |
| A3 | gateA3-claude minor | teaser with no second beat >= 5 plies away fails at script stage | defer | Fail closed per spec section 2; spare games fill the slot. |
