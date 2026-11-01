# Fish batch: five long-form videos

Run: https://github.com/codewithpom/chesscode/actions/runs/41324471349
Branch: `upload/five-long-20261101`
Channel: Chess Code (`UCtY66nnxSJuW8tT64WvvcFg`)

Status: all five videos rendered, but none uploaded. All QA checks passed except `black_frames`: FFmpeg's default 10% luma threshold incorrectly classified the intentional #0F1115 Studio cards/outro as black. Contact sheets and thumbnails were visually checked. A regression test reproduced the false positive; black-pixel threshold is now 2%, and all 12 QA tests pass, including real-black-frame rejection. Five per-video voice caches are saved, so the next run needs no new synthesis. Failed-QA events are preserved in `data/upload_log.csv`.

Earlier run 41322641166 was cancelled after the metadata name-shape bug. Metadata now reads PGN facts; five real-content tests reach a valid spec, and metadata/workflow/E2E checks pass. Current workflow includes a final read-back of YouTube ids, privacy and publish times.

Provider: `fish`, model `s2.1-pro-free`. Credentials are in GitHub Secrets. Both language smoke tests and 356 Python tests passed (1 skipped); 39 targeted tests cover the latest provider edge cases.

| video | expected publish time (UTC) |
| --- | --- |
| cc-2026-0005-hi | 2026-12-17T13:30:00Z |
| cc-2026-0006-en | 2026-12-22T18:30:00Z |
| cc-2026-0006-hi | 2026-12-24T13:30:00Z |
| cc-2026-0007-en | 2026-12-29T18:30:00Z |
| cc-2026-0007-hi | 2026-12-31T13:30:00Z |
