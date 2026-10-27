from .base import TTSBackend


def get_tts_backend(cfg) -> TTSBackend:
    """Return configured TTS backend. Fallback chain: kokoro -> elevenlabs -> gtts."""
    backend = cfg.active_tts_backend  # property already resolves fallback
    if backend == "kokoro":
        from .kokoro_backend import KokoroBackend
        return KokoroBackend(voice_en=cfg.kokoro_voice_en, voice_hi=cfg.kokoro_voice_hi)
    if backend == "elevenlabs":
        from .elevenlabs_backend import ElevenLabsBackend
        return ElevenLabsBackend(
            api_key=cfg.elevenlabs_api_key,
            voice_en=cfg.voice_en,
            voice_hi=cfg.voice_hi,
        )
    from .gtts_backend import GTTSBackend
    return GTTSBackend()


__all__ = ["TTSBackend", "get_tts_backend"]
