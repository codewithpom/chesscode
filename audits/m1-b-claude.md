# M1 re-audit (fixes + Tasks 4-5), commit 44d5aa7, by Claude

Suite: `cd pipeline && python -m pytest -q` gives 42 passed (Windows, Python 3.12).

## Previous findings (m1-a-claude.md)

verified-fixed | pipeline/chesscode/auth.py:13-15,66-69 + .gitignore:12,17 | Token and client_secret paths are now anchored to the repo root, and the token is chmod 0600. `git check-ignore` matches both pipeline/data/secrets/youtube_token.json and data/secrets/* through `**/data/secrets/`. | -
verified-fixed | pipeline/chesscode/tts/azure.py:23-27 + tts/__init__.py:34-35 | Duration handles timedelta, non-Word boundaries are skipped, and an empty word list raises instead of being cached. A fake-event test exists (test_tts.py). | -
verified-fixed | pipeline/chesscode/tts/align.py:12,19-20 | It aligns the known `text` through whisperx.align, and a missing start/end falls back to an estimate instead of raising KeyError. | -
verified-fixed | pipeline/chesscode/tts/elevenlabs.py:52 | Prefers `alignment`, falls back to normalized. | -
verified-fixed | pipeline/chesscode/upload.py:95-97 | find_existing runs before each retry. The CSV is deferred per TRIAGE. | -
verified-fixed | pipeline/tests/test_auth.py:38-67 | Sentinel env token, mocked login, and stdout/stderr asserted clean. | -
verified-fixed | pipeline/tests/test_auth.py:70-77 | RefreshError is now raised from Credentials.refresh. | -
verified-fixed | pipeline/chesscode/auth.py:60-61 | FileNotFoundError, KeyError, IndexError and HttpError are wrapped in AuthError with an "auth login" hint. | -
verified-fixed | pipeline/chesscode/upload.py:21-26,40 | Microseconds are stripped, containsSyntheticMedia is set, and title and description lengths are validated (the description after the footer). | -
verified-fixed | pipeline/chesscode/upload.py:91 + tests/test_upload.py:95-140 | http.client and httplib2 errors are retried. There are tests for 4xx no-retry, socket retry and the playlist check. | -
verified-fixed | pipeline/chesscode/tts/elevenlabs.py:29-39,63-65 | The HTTP status is reported, and requests are chunked at 10K chars. | -
verified-fixed | pipeline/chesscode/tts/__init__.py:26-37 | The raw output is kept as `<key>.raw.mp3` with words.json written before loudnorm, so a loudnorm failure does not re-bill. The key change is deferred per TRIAGE. | -
verified-fixed | pipeline/tests/test_tts.py:21 | Codepoints match the plan string (a single nukta U+093C). | -
verified-fixed | scripts/day1_upload_test.py:27-28,39 | The guard runs and the real build_body output is printed in dry-run. | -

## New code

major | .github/workflows/timing.yml:50-51 | `npx remotion benchmark` is unscoped: no composition, no `--props`, no `--public-dir`. remotion/public does not exist, so the fixture's `staticFile` narration audio returns 404 and the benchmark fails. It also renders the full composition several times by default. The step runs under `bash -e`, so the failure exits before line 51, and the `render_seconds=` summary line (Task 5's only output) is never written. | Write the summary line right after the render. Then run `npx remotion benchmark src/index.ts StudioVideo --props=... --public-dir=... --runs=1` (or add `|| true`) and append its output to $GITHUB_STEP_SUMMARY, as the plan asks.
minor | .github/workflows/timing.yml:12 | There is no `permissions:` block, so GITHUB_TOKEN gets the repository's default scope. No secrets are used or echoed, and inputs are passed through env, so there is no injection. | Add `permissions: { contents: read }`.
minor | pipeline/tests/test_bakeoff.py:18 | It asserts a Windows path (`build\\bakeoff\\kokoro_en.mp3`), so it fails on Linux/CI. | Build the expected text with `Path("build/bakeoff/kokoro_en.mp3")`, or assert on `kokoro_en.mp3` only.
minor | scripts/tts_bakeoff.py:26,30 | The placeholder check matches only the `TODO` prefix. An empty or null YAML value becomes "None" or "" and goes to a paid provider, and a missing provider key raises KeyError. | Refuse when the value is falsy or starts with TODO, and give a clear message when the provider or lang is missing.
minor | pipeline/chesscode/tts/elevenlabs.py:57-58 | The offset for the next chunk is the last word's end_ms, not the chunk's real audio length. Trailing silence and MP3 frame padding make the captions drift with each chunk (this only applies to texts over 10K chars). | Advance the offset by the chunk's decoded audio duration, or by the last character end time of its alignment.
minor | pipeline/chesscode/tts/align.py:19-20 | The missing-timestamp fallback is spread uniformly by index, so it can overlap or come before neighbouring aligned words. | Interpolate between the previous word's end and the next word's start.
minor | pipeline/chesscode/auth.py:66 | `auth login` with no client_secret.json shows a raw FileNotFoundError traceback. | Wrap it in AuthError that names the expected path.
minor | scripts/day1_upload_test.py:25,27 | `--publish-in-hours 2` is always refused, because later calls see a "now" that has moved past the exact 2 h mark. The plan uses 24, so this is cosmetic. | Document a minimum of 3, or compare with a small tolerance.

Bake-off check: placeholder providers are refused before any provider call (the check runs for all providers in the first loop). Keys are never printed (the ElevenLabs error text is sanitized and no env values are echoed). All outputs and the cache go under build/bakeoff, which is git-ignored. index.html has every column the plan requires, with escaped values. The workflow otherwise matches plan Task 5 exactly: workflow_dispatch only, ubuntu-24.04, Node 22 with npm cache, the full Chrome dependency list, `--public-dir` on the render, no artifact upload, and the frame-range input validated.

Verdict: NOT READY. One major: timing.yml's benchmark step fails and suppresses the required render_seconds summary. It is a two-line fix. Everything else is ready.
