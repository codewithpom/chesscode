# Five Fish Audio videos: uploaded and verified

All five videos passed all eight automated QA checks, uploaded successfully, and were independently read back from YouTube. Each is private with the intended future publication time, a matching ccid, and an accepted upload status. No thumbnail or playlist repair is pending.

- Channel: Chess Code (`UCtY66nnxSJuW8tT64WvvcFg`).
- Workflow: https://github.com/codewithpom/chesscode/actions/runs/41326509860
- Rendered commit: `87707c3`; branch: `upload/five-long-20261101`.
- TTS: Fish Audio `s2.1-pro-free`, fixed licensed English/Hindi voices; credentials remain in GitHub Secrets.
- YouTube verification receipt: [verified ids and UTC times](five-long-fish-20261101.youtube.json).
- Ledger: `data/upload_log.csv` retains the failed-QA attempt and the five successful scheduled events.

Publication dates below use **India Standard Time (UTC+05:30)**. English midnight slots fall on the following local date compared with the UTC calendar.

| Video | YouTube | Publication (IST) | Duration |
| --- | --- | --- | --- |
| Morphy: Opera Game (Hindi) | https://youtu.be/oGovuQckbVQ | 2026-12-17 19:00 | 8:51 |
| Gukesh vs Ding, Game 3 (English) | https://youtu.be/pbEEe6ktXGU | 2026-12-23 00:00 | 9:04 |
| Gukesh vs Ding, Game 3 (Hindi) | https://youtu.be/BOFQqwZ4zBk | 2026-12-24 19:00 | 9:10 |
| Spassky vs Bronstein (English) | https://youtu.be/4JyE-OuDRLY | 2026-12-30 00:00 | 9:37 |
| Spassky vs Bronstein (Hindi) | https://youtu.be/U2d8GOW6J3M | 2026-12-31 19:00 | 9:51 |

QA covered schema/calendar/pacing, SAN legality, mascot line rules, segment loudness, final mixed loudness/true peak, unplanned silence, genuine black frames, and output codec/size/fps/duration. Contact sheets and thumbnails were visually checked; the complete videos have not been watched end to end by a human.

Fish is free under its fair-use and concurrency rules, without a latency guarantee. The Studio black-frame regression was fixed by calibrating black-pixel luma below the intentional dark background; a real black segment still fails the check. No QA override was used.

Audio was restored from per-video caches on the final run. The configured background music remains a silent placeholder. Main has not been merged; the working upload system and these receipts are on the branch above.

Receipts collected: 2026-11-01T16:43:07+00:00.
