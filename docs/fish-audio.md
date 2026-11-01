# Fish Audio narration

The owner selected Fish Audio S2.1 Pro Free on November 1, 2026. The provider uses the existing `Synth` contract, TTS cache and loudness normalization. No SDK dependency or paid transcription call is needed.

- Model is fixed to `s2.1-pro-free`, in both the model header and the compatibility request body. There is no paid-model fallback.
- `FISH_API_KEY` is a GitHub Actions repository secret. Preflight verifies access without requiring a positive paid-credit balance.
- English uses the licensed Calm Narrator Voice (`6d71c24e892b467ebef21f3dd3f4810a`); Hindi uses the licensed Hindi voice `18e8999c98b746bda58521980d817e8c`. Both were queried with `licensed=true` and tested successfully.
- The ElevenLabs-compatible timestamp endpoint returns audio and character alignment together. Existing character-to-word conversion preserves the caption pipeline. Fish documents these character times as interpolated from segment timestamps; switch to native word timestamps if visible drift appears.
- Default `normal` latency prioritizes quality. Language is left unset for mixed Hindi/English narration, as recommended by Fish. Existing segment boundaries keep requests short, and fixed reference voices keep the narration consistent.
- HTTP 429 and transient server errors retry with bounded exponential backoff. Authentication and billing errors stop immediately. Incomplete audio or alignment is never saved as a successful response.
- Free generation is subject to fair-use and concurrency limits; it is not a promise of unlimited throughput or a latency guarantee. The workflow runs two videos at once.

Smoke tests: English and Hindi both returned HTTP 200 with audio and alignment. Automated tests cover free-model selection, Hindi word timings, retries, invalid alignment, secret-safe failures and workflow credentials.

## Official sources

- [Quick Start](https://docs.fish.audio/developer-guide/getting-started/quickstart)
- [Pricing and rate limits](https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits)
- [Models](https://docs.fish.audio/developer-guide/models-pricing/models-overview)
- [ElevenLabs compatibility and timestamps](https://docs.fish.audio/developer-guide/compat/migrate-from-elevenlabs)
- [Native synthesis and mixed-language normalization](https://docs.fish.audio/features/text-to-speech)
