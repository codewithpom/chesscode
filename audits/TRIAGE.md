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
