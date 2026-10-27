# M1 Day-1 Risk Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the code that de-risks day one: OAuth + `auth check`, a guarded scheduled upload with a throwaway test video, the TTS bake-off (ElevenLabs, Azure, Kokoro × EN/HI), and an Actions workflow that times a Remotion render.

**Architecture:** Python modules inside `pipeline/chesscode/` reached through the Phase-0 CLI dispatcher (`chesscode.auth`, `chesscode.upload` expose `main(args) -> int`). TTS adapters share one interface in `chesscode/tts/` so the M2 `voice` stage reuses them. Live calls happen only in `scripts/` and only after the owner confirms.

**Tech Stack:** Python 3.12, google-api-python-client, google-auth-oauthlib, requests, azure-cognitiveservices-speech, kokoro-onnx, whisperx (alignment), imageio-ffmpeg, pytest; GitHub Actions, Node 22, Remotion 4.0.539.

**Spec:** `docs/SPEC.md` sections 4 (TTS), 9 (Actions), 10 (upload, OAuth, quota). Roadmap: `docs/ROADMAP.md`.

## Global Constraints

- Every remote call is mocked in tests; no test touches the network or a real account.
- Secrets come from env vars or git-ignored `data/secrets/`; never printed, logged, or committed. The repo is **public**.
- OAuth client type Desktop app; scopes exactly `https://www.googleapis.com/auth/youtube.upload` and `https://www.googleapis.com/auth/youtube`.
- Upload: `privacyStatus: "private"`, `publishAt` UTC ISO 8601, `selfDeclaredMadeForKids: false`, `categoryId: "20"`; refuse when `publishAt` is in the past or less than 2 h ahead.
- Resumable upload (`MediaFileUpload(resumable=True)`), retry 5xx and network errors with exponential backoff, max 5 tries.
- Description ends with footer line `ccid: <video_id>`.
- Audio: ffmpeg `loudnorm` to -14 LUFS integrated, -1 dBTP; 48 kHz MP3. ffmpeg binary = `imageio_ffmpeg.get_ffmpeg_exe()`.
- TTS cache key = sha256 of `(provider, voice, text)`; cached file reused, never re-billed.
- Word timings are mandatory: `list[Word]` where `Word = {"w": str, "start_ms": int, "end_ms": int}`, offsets relative to the start of that audio file.
- Workflows: `workflow_dispatch` only for anything that renders; artifacts never contain MP4s.

## Review Focus

1. Clock skew / timezone: a naive `datetime` passed as `publish_at` must be rejected, not treated as local time → test in Task 2.
2. A refresh token from a "Testing" consent screen expires in 7 days; `auth check` must fail loudly with a message naming the consent-screen status, not a stack trace → test in Task 1.
3. ElevenLabs character timestamps for Devanagari: grouping on spaces must keep matras/conjuncts inside one word → test in Task 3 with a Hindi string.
4. Re-running the day-1 script must not create a second upload → `ccid` lookup test in Task 2.
5. Secrets leaking into logs via exception messages (e.g. `requests` URL with key) → test that error text never contains the key in Task 3.

---

### Task 1: OAuth login and `auth check`

**Files:**
- Create: `pipeline/chesscode/auth.py`
- Test: `pipeline/tests/test_auth.py`
- Reference: `legacy/token_setup.py`, `legacy/youtube_uploader.py` (port the flow; legacy stays untouched)

**Interfaces:**
- Consumes: CLI `python -m chesscode auth login|check` (dispatcher in `chesscode/__main__.py`).
- Produces:
  - `SCOPES: list[str]`
  - `TOKEN_PATH = Path("data/secrets/youtube_token.json")`
  - `load_credentials() -> google.oauth2.credentials.Credentials` — from env `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` if set, else `TOKEN_PATH`; refreshes; raises `AuthError` with an actionable message on `invalid_grant`.
  - `youtube_client() -> googleapiclient.discovery.Resource`
  - `check() -> dict` returning `{"channel_id": str, "title": str}` from `channels.list(part="snippet", mine=True)`.
  - `main(args) -> int` (`login` runs `InstalledAppFlow.from_client_secrets_file("data/secrets/client_secret.json", SCOPES).run_local_server()` and writes `TOKEN_PATH`; `check` prints channel title, never the token).

- [ ] **Step 1: Write failing tests** `test_check_returns_channel` (mock client returns one channel → dict), `test_invalid_grant_raises_auth_error_mentioning_consent_screen` (refresh raises `RefreshError("invalid_grant")` → `AuthError` whose message contains `"In production"`), `test_env_credentials_preferred_over_file`, `test_check_output_never_contains_refresh_token` (capsys).
- [ ] **Step 2:** `cd pipeline && pytest tests/test_auth.py -v` → FAIL (module missing).
- [ ] **Step 3:** Implement `auth.py` per Interfaces.
- [ ] **Step 4:** `pytest tests/test_auth.py -v` → PASS.
- [ ] **Step 5:** Commit `feat(auth): OAuth login and auth check`.

### Task 2: Guarded scheduled upload + day-1 script

**Files:**
- Create: `pipeline/chesscode/upload.py`, `scripts/day1_upload_test.py`
- Test: `pipeline/tests/test_upload.py`

**Interfaces:**
- Consumes: `auth.youtube_client()`.
- Produces:
  - `class UploadRefused(Exception)`
  - `check_publish_at(publish_at: datetime, now: datetime) -> None` — raises `UploadRefused` if `publish_at.tzinfo is None`, in the past, or `< now + 2h`.
  - `with_ccid_footer(description: str, video_id: str) -> str` — appends `\n\nccid: <video_id>` once (idempotent).
  - `find_existing(client, video_id: str) -> str | None` — pages the channel uploads playlist (`channels.list(contentDetails)` → `playlistItems.list`, 50 per page) for a description containing `ccid: <video_id>`; returns YouTube id.
  - `upload_video(client, path: Path, video_id: str, title: str, description: str, tags: list[str], publish_at: datetime, language: str, now: datetime | None = None) -> str` — guard, dedupe via `find_existing`, resumable insert with retry (5 tries, backoff 2**n s, 5xx/`socket.error` only), returns YouTube id.
  - `main(args) -> int` — M1 stub: prints "full uploader lands in M7" and returns 2 (spec-folder upload comes later).
- `scripts/day1_upload_test.py --publish-in-hours 24 [--dry-run]`: renders a 5 s 1280×720 test clip via ffmpeg (`testsrc` + `sine`), title `ChessCode API test (delete me)`, video_id `cc-test-0000-en`, calls `upload_video`, prints YouTube Studio URL. `--dry-run` stops before the insert.

- [ ] **Step 1: Write failing tests** `test_refuses_naive_datetime`, `test_refuses_past`, `test_refuses_under_two_hours` (now+1h59m), `test_accepts_two_hours_ahead` (now+2h01m), `test_ccid_footer_idempotent`, `test_find_existing_pages_through_playlist` (2 pages, match on page 2), `test_upload_skips_when_ccid_exists` (insert never called), `test_upload_body_private_with_publish_at` (asserts `status.privacyStatus == "private"`, `publishAt` ends in `Z`, `selfDeclaredMadeForKids is False`, `snippet.categoryId == "20"`, `defaultLanguage == defaultAudioLanguage == language`), `test_retries_5xx_then_succeeds`, `test_gives_up_after_5_tries`.
- [ ] **Step 2:** `pytest tests/test_upload.py -v` → FAIL.
- [ ] **Step 3:** Implement `upload.py` and the script.
- [ ] **Step 4:** `pytest tests/test_upload.py -v` → PASS; `python scripts/day1_upload_test.py --dry-run` → prints the request body and clip path, no network.
- [ ] **Step 5:** Commit `feat(upload): guarded scheduled upload and day-1 test script`.
- [ ] **Step 6: `[HUMAN]` STOP.** Owner provides the OAuth client, sets the consent screen to "In production", runs `python -m chesscode auth login` once, confirms the real upload. Then run the script; owner checks Studio shows **Scheduled** (not Locked) and, later, that it goes public. If Locked: owner submits the audit form the same day (ROADMAP fallback).

### Task 3: TTS adapters with word timings

**Files:**
- Create: `pipeline/chesscode/tts/__init__.py`, `tts/base.py`, `tts/elevenlabs.py`, `tts/azure.py`, `tts/kokoro.py`, `tts/align.py`, `pipeline/chesscode/audio.py`
- Test: `pipeline/tests/test_tts.py`, `pipeline/tests/test_audio.py`
- Reference: `legacy/tts_backends/elevenlabs_backend.py`, `legacy/tts_backends/kokoro_backend.py`

**Interfaces:**
- Produces:
  - `tts.base.Word = TypedDict("Word", {"w": str, "start_ms": int, "end_ms": int})`
  - `tts.base.Synth = Callable[[str, str, str, Path], list[Word]]` — `(text, voice, lang, out_mp3) -> words`
  - `tts.synthesize(provider: str, text: str, voice: str, lang: str, cache_dir: Path) -> tuple[Path, list[Word]]` — cache lookup by `cache_key`, else dispatch, then `audio.loudnorm`; words stored next to the mp3 as `<key>.words.json`.
  - `tts.cache_key(provider: str, voice: str, text: str) -> str` (sha256 hex)
  - `tts.elevenlabs.chars_to_words(chars: list[str], starts_s: list[float], ends_s: list[float]) -> list[Word]` — group on whitespace.
  - `tts.azure` uses `azure.cognitiveservices.speech` `synthesis_word_boundary` events (`audio_offset` in 100 ns ticks → ms).
  - `tts.kokoro` synthesizes locally (model path env `KOKORO_MODEL`, `KOKORO_VOICES`), then `tts.align.align_words(mp3: Path, text: str, lang: str) -> list[Word]` via WhisperX.
  - `audio.loudnorm(src: Path, dst: Path) -> None` — two-pass `loudnorm=I=-14:TP=-1:LRA=11`, `-ar 48000`, MP3.
  - `audio.measure(path: Path) -> dict` with `input_i`, `input_tp` floats (parsed from loudnorm JSON).

- [ ] **Step 1: Write failing tests** `test_chars_to_words_english` (`"Hi there"` → 2 words with first-char start / last-char end ms), `test_chars_to_words_hindi_keeps_matras` (`"घोड़ा फँस गया"` → exactly 3 words, text equal to the space-split tokens), `test_azure_ticks_to_ms` (10_000 ticks → 1 ms), `test_cache_hit_skips_provider` (second call does not invoke the synth), `test_cache_key_changes_with_voice`, `test_provider_error_message_hides_key` (env key `sk-secret` absent from raised message), `test_loudnorm_hits_target` (generate 2 s sine with ffmpeg, normalize, `measure` → `-15 <= input_i <= -13` and `input_tp <= -1.0`).
- [ ] **Step 2:** `pytest tests/test_tts.py tests/test_audio.py -v` → FAIL.
- [ ] **Step 3:** Implement. Add `azure-cognitiveservices-speech`, `kokoro-onnx`, `whisperx` under `[project.optional-dependencies] tts` in `pipeline/pyproject.toml` (heavy; not needed by CI tests, which mock them).
- [ ] **Step 4:** Tests PASS.
- [ ] **Step 5:** Commit `feat(tts): ElevenLabs, Azure and Kokoro adapters with word timings`.

### Task 4: Bake-off script and listening page

**Files:**
- Create: `scripts/tts_bakeoff.py`, `content/bakeoff/en.txt`, `content/bakeoff/hi.txt`

**Interfaces:**
- Consumes: `tts.synthesize`.
- Produces: `build/bakeoff/<provider>_<lang>.mp3`, `<provider>_<lang>.words.json`, `build/bakeoff/index.html` (one row per sample: provider, voice, lang, `<audio controls>`, word count, first 10 words with timings, LUFS).
- Scripts: ~150 words EN, ~140 words HI, about the Opera Game, written natively (HI in conversational Hindi with chess terms in English, spec section 8 register — not a translation). The main session writes these two texts.
- Voices: `--voices config/bakeoff_voices.yaml` maps provider → lang → voice id (ElevenLabs multilingual v2 voice, Azure `en-IN`/`hi-IN` neural voices from the voice list API, Kokoro EN + Hindi voices).

- [ ] **Step 1:** `python scripts/tts_bakeoff.py --providers kokoro --dry-run` lists planned outputs without calling providers.
- [ ] **Step 2:** Run with `--providers kokoro` (local, no key) → 2 mp3 + words + index.html. Verify `audio.measure` within ±1 LU.
- [ ] **Step 3:** Commit `feat(tts): bake-off script`.
- [ ] **Step 4: `[HUMAN]` STOP for keys.** Owner exports `ELEVENLABS_API_KEY`, `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`; run all providers; publish `index.html` as a private Artifact; owner picks voices (M3 checkpoint).

### Task 5: Actions render timing

**Files:**
- Create: `.github/workflows/timing.yml`

**Interfaces:**
- Consumes: `remotion/` `StudioVideo` composition and `spec/fixtures/cc-2026-0001-en/`.
- Produces: job summary line `render_seconds=<n> frames=<n> runner=<vCPU>`.

- [ ] **Step 1:** Workflow: `workflow_dispatch` with input `frames` (default `0-1799`, 60 s); `ubuntu-24.04`; `actions/setup-node` 22 with npm cache on `remotion/package-lock.json`; install the Remotion Ubuntu 24.04 Chrome deps (`libnss3 libdbus-1-3 libatk1.0-0 libgbm-dev libasound2t64 libxrandr2 libxkbcommon-dev libxfixes3 libxcomposite1 libxdamage1 libatk-bridge2.0-0 libpango-1.0-0 libcairo2 libcups2t64`); `npm ci`; `npx remotion browser ensure`; time `npx remotion render StudioVideo /tmp/out.mp4 --props=../spec/fixtures/cc-2026-0001-en/video_spec.json --public-dir=../spec/fixtures/cc-2026-0001-en --frames=${{ inputs.frames }} --codec=h264 --crf=18 --x264-preset=veryfast --concurrency=100%`; also `npx remotion benchmark` summary; write to `$GITHUB_STEP_SUMMARY`. No artifact upload.
- [ ] **Step 2:** `gh workflow run timing.yml` after merge to main; `gh run watch`; record the number in `docs/ROADMAP.md` under M1. Re-run once remotion-core merges (placeholder render is cheaper than the real board).
- [ ] **Step 3:** Commit `ci: render timing workflow`.
