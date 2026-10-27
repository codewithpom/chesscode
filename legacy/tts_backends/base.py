"""Base class for TTS backends.

All TTS backends must inherit from TTSBackend and implement the synthesize method.
"""

from abc import ABC, abstractmethod
from typing import Literal

__all__ = ["TTSBackend"]


class TTSBackend(ABC):
    """Abstract base for text-to-speech backends."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        language: str = "en",
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize text to audio.
        
        Args:
            text: Text to synthesize
            language: Language code ('en' or 'hi')
            speed: Playback rate multiplier (1.0 = normal). Backends without native
                   speed control (ElevenLabs, gTTS) may ignore this.
        
        Returns:
            WAV or MP3 bytes
        """
        ...
