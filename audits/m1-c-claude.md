# M1 third audit, commit a021585, by Claude

Suite: `cd pipeline && python -m pytest -q` gives 48 passed (Windows).

## Findings from m1-b-claude.md

verified-fixed | .github/workflows/timing.yml:52-53 | render_seconds is written to $GITHUB_STEP_SUMMARY right after the render. The benchmark now has composition, --props, --public-dir and --runs=1, ends with `|| true`, and src/index.ts exists. | -
verified-fixed | .github/workflows/timing.yml:15-16 | `permissions: contents: read` added. | -
verified-fixed | pipeline/tests/test_bakeoff.py:18 | The expected text is built with Path(), so it is OS-independent. | -
verified-fixed | scripts/tts_bakeoff.py:26-29,62-67 | Empty, None, TODO-prefixed and missing provider/lang values are refused (exit 2) before any provider call. Tests exist for empty and missing values. | -
verified-fixed | pipeline/chesscode/tts/elevenlabs.py:57-58 | The chunk offset now advances by max(character_end_times_seconds), and a test covers it. | -
verified-fixed | pipeline/chesscode/tts/align.py:19-32 | Missing timestamps are interpolated between the previous end and the next start (or the duration). A test covers it. | -
verified-fixed | pipeline/chesscode/auth.py:66-71 | A missing client_secret.json prints the path and returns 1, with no traceback. A test covers it. | -
verified-fixed | scripts/day1_upload_test.py:18-28 | A minimum of 3 h is enforced, and a test covers it. | -

## Workflow checks (timing.yml)

verified | .github/workflows/timing.yml:3-4 | The only trigger is workflow_dispatch. No secrets are referenced. The input goes through env and is regex-validated. There is no upload-artifact step, so the MP4 is not kept. | -

## New problems

minor | .github/workflows/timing.yml:13-14,53 | The job has no `timeout-minutes`. `remotion benchmark` ignores the frame range and renders the full composition once per default concurrency value, so it can run for a long time on a failing or slow runner. The 6 h default limit applies. | Add `timeout-minutes: 45` and pass `--concurrencies=<n>`.
minor | .github/workflows/timing.yml:53 | The benchmark's progress output (ANSI) is appended to the step summary, so it renders as noise. | Redirect to a file and append only the final table, or keep as is.
minor | scripts/day1_upload_test.py:18-23 | An argparse `type=` that raises UploadRefused (not ArgumentTypeError/ValueError) produces a raw traceback instead of a usage error. | Raise argparse.ArgumentTypeError.
info | scripts/day1_upload_test.py:20 + pipeline/chesscode/upload.py:49 | The 3 h minimum is a CLI-only choice. The library guard stays at 2 h (7200 s), which matches SPEC section 10 and the plan. The change to 3 h breaks nothing: the SPEC and plan day-1 step use 24 h, and the tests pass 3. It only gives a margin because "now" moves between the CLI check and the library check. | -

Verdict: READY TO MERGE
