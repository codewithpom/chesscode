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
