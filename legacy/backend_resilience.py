"""backend_resilience.py — Resilient wrappers for LLM and TTS backends with fallback & timeout.

This module wraps LLM and TTS backend calls with:
- Timeout protection (configurable per operation)
- Automatic fallback chains (Claude → Ollama, ElevenLabs → Kokoro → gTTS)
- Structured error logging
- Graceful degradation
"""

import logging
import functools
from typing import Callable, Any, Optional, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError

logger = logging.getLogger(__name__)

__all__ = [
    "call_with_timeout",
    "resilient_llm_call",
    "resilient_tts_call",
    "BackendError",
]


class BackendError(Exception):
    """Raised when a backend call fails after all fallback attempts."""
    pass


def call_with_timeout(
    func: Callable[..., Any],
    timeout_seconds: float,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Call func with a timeout. If timeout is exceeded, raises TimeoutError.
    
    Args:
        func: Callable to invoke
        timeout_seconds: Maximum time in seconds
        *args, **kwargs: Arguments to pass to func
    
    Returns:
        Result of func(*args, **kwargs)
    
    Raises:
        TimeoutError: If call takes longer than timeout_seconds
    """
    if timeout_seconds <= 0:
        return func(*args, **kwargs)  # No timeout
    
    result = [None]
    exception = [None]
    
    def _run():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=_run, daemon=False)
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        logger.error(f"Function {func.__name__} exceeded timeout of {timeout_seconds}s")
        raise TimeoutError(f"Call to {func.__name__} timed out after {timeout_seconds}s")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]


def resilient_llm_call(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    timeout_seconds: float = 60.0,
) -> str:
    """
    Make an LLM call with automatic fallback and timeout.
    
    Fallback chain: Claude → Ollama → Dummy response (empty string)
    
    Args:
        system_prompt: System context
        user_prompt: User's request
        max_tokens: Max tokens in response
        timeout_seconds: Timeout per call (0 = no timeout)
    
    Returns:
        Generated text
    
    Raises:
        BackendError: If all backends fail
    """
    from config import cfg
    
    backends_to_try = []
    
    # Try Claude first if available
    if cfg.has_anthropic:
        backends_to_try.append(("Claude", lambda: (
            __import__("llm_backends").claude_backend.ClaudeBackend(
                api_key=cfg.anthropic_api_key
            ).generate(system_prompt, user_prompt, max_tokens)
        )))
    
    # Try Ollama next if configured
    if cfg.has_ollama:
        backends_to_try.append(("Ollama", lambda: (
            __import__("llm_backends").ollama_backend.OllamaBackend(
                url=cfg.ollama_url,
                model=cfg.ollama_model,
            ).generate(system_prompt, user_prompt, max_tokens)
        )))
    
    # Try each backend in order
    last_error = None
    for backend_name, backend_func in backends_to_try:
        try:
            logger.info(f"Trying LLM backend: {backend_name}")
            result = call_with_timeout(backend_func, timeout_seconds)
            logger.info(f"✓ {backend_name} succeeded")
            return result
        except TimeoutError as e:
            logger.warning(f"⏱ {backend_name} timed out: {e}")
            last_error = e
        except Exception as e:
            logger.warning(f"✗ {backend_name} failed: {e}")
            last_error = e
    
    # All backends failed
    logger.error(f"All LLM backends failed. Last error: {last_error}")
    raise BackendError(f"LLM call failed after trying all backends: {last_error}")


def resilient_tts_call(
    text: str,
    language: str = "en",
    speed: float = 1.0,
    timeout_seconds: float = 30.0,
) -> bytes:
    """
    Synthesize text to audio with automatic fallback and timeout.
    
    Fallback chain: Configured backend (Kokoro/ElevenLabs) → gTTS
    
    Args:
        text: Text to synthesize
        language: Language code ('en' or 'hi')
        speed: Playback speed multiplier
        timeout_seconds: Timeout per call (0 = no timeout)
    
    Returns:
        Audio bytes (WAV or MP3)
    
    Raises:
        BackendError: If all backends fail
    """
    from config import cfg
    from tts_backends import get_tts_backend
    
    # Primary backend from config
    backends_to_try = [
        ("Primary TTS", lambda: get_tts_backend(cfg).synthesize(text, language, speed))
    ]
    
    # gTTS as fallback (always available)
    if cfg.active_tts_backend != "gtts":
        from tts_backends.gtts_backend import GTTSBackend
        backends_to_try.append(
            ("gTTS (fallback)", lambda: GTTSBackend().synthesize(text, language, speed))
        )
    
    last_error = None
    for backend_name, backend_func in backends_to_try:
        try:
            logger.debug(f"Trying TTS backend: {backend_name}")
            result = call_with_timeout(backend_func, timeout_seconds)
            logger.debug(f"✓ {backend_name} succeeded")
            return result
        except TimeoutError as e:
            logger.warning(f"⏱ {backend_name} timed out: {e}")
            last_error = e
        except Exception as e:
            logger.warning(f"✗ {backend_name} failed: {e}")
            last_error = e
    
    # All backends failed
    logger.error(f"All TTS backends failed. Last error: {last_error}")
    raise BackendError(f"TTS synthesis failed after trying all backends: {last_error}")
