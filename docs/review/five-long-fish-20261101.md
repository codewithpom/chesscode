# Fish batch: five long-form videos

Run: https://github.com/codewithpom/chesscode/actions/runs/41322641166
Branch: `upload/five-long-20261101`
Channel: Chess Code (`UCtY66nnxSJuW8tT64WvvcFg`)

Status: the first Fish run was cancelled after its first two videos completed speech synthesis but failed at metadata (`'str' object has no attribute 'get'`). No uploads occurred. Metadata now reads authoritative PGN facts; five real-content tests reach a valid emitted spec using synthetic voice timing. Cache preservation and cancellation have also been fixed. A fresh run is required.

Provider: `fish`, model `s2.1-pro-free`. Credentials are in GitHub Secrets. Both language smoke tests and 356 Python tests passed (1 skipped); 39 targeted tests cover the latest provider edge cases.

| video | expected publish time (UTC) |
| --- | --- |
| cc-2026-0005-hi | 2026-12-17T13:30:00Z |
| cc-2026-0006-en | 2026-12-22T18:30:00Z |
| cc-2026-0006-hi | 2026-12-24T13:30:00Z |
| cc-2026-0007-en | 2026-12-29T18:30:00Z |
| cc-2026-0007-hi | 2026-12-31T13:30:00Z |
