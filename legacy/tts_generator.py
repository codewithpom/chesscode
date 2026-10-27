"""tts_generator.py — TTS generation using the configured backend."""

import os
import shutil
import struct
import wave
import io
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

logger = logging.getLogger(__name__)


class TTSGenerator:
    """Generates TTS audio files for a list of text segments.

    Wraps the tts_backends package. Supports language="en" or "hi".
    prefer_elevenlabs / elevenlabs_api_key / voice_id are legacy params kept
    for backwards-compat with existing main.py calls — they are ignored when
    TTS_BACKEND env var is set to something other than "elevenlabs".
    """

    def __init__(
        self,
        language: str = "en",
        prefer_elevenlabs: bool = False,
        elevenlabs_api_key: str = "",
        voice_id: str = "",
    ):
        self._language = language
        from config import cfg
        from tts_backends import get_tts_backend
        self._backend = get_tts_backend(cfg)
        self._cache_dir = cfg.tts_cache_dir
        self._voice = (getattr(self._backend, f"_voice_{language}", "")
                       or getattr(self._backend, "_voice_en", ""))

    def generate_batch(self, segments: List[str], output_dir: str) -> List[str]:
        """Synthesize each segment and save to output_dir. Returns list of file paths, in order.

        Runs segments concurrently — Kokoro's ONNX session.Run() is thread-safe for
        concurrent calls (verified: parallel output byte-identical to sequential).
        Identical (backend, voice, language, text) segments are served from a
        content-addressed cache instead of resynthesizing.
        """
        from cache_utils import cache_key, get_cached, put_cached

        os.makedirs(output_dir, exist_ok=True)
        tasks = [(i, text.strip()) for i, text in enumerate(segments) if text and text.strip()]
        backend_name = type(self._backend).__name__

        def _synth_one(i: int, text: str) -> str:
            from emotion_tags import parse_emotion
            clean_text, speed = parse_emotion(text)
            key = cache_key(backend_name, self._language, self._voice, str(speed), clean_text)
            try:
                cached = get_cached(self._cache_dir, key, ".wav") or get_cached(self._cache_dir, key, ".mp3")
                if cached:
                    ext = os.path.splitext(cached)[1]
                    out_path = os.path.join(output_dir, f"seg_{i:03d}{ext}")
                    shutil.copyfile(cached, out_path)
                    logger.debug(f"TTS segment {i}: cache hit → {out_path}")
                    return out_path

                audio_bytes = self._backend.synthesize(clean_text, language=self._language, speed=speed)
                # Kokoro returns WAV — write it directly, no MP3 conversion needed
                # since downstream consumers (moviepy/ffmpeg) read WAV natively.
                # Other backends (ElevenLabs/gTTS) already return compressed bytes.
                ext = ".wav" if _is_wav(audio_bytes) else ".mp3"
                out_path = os.path.join(output_dir, f"seg_{i:03d}{ext}")
                with open(out_path, "wb") as f:
                    f.write(audio_bytes)
                put_cached(self._cache_dir, key, ext, out_path)
                logger.debug(f"TTS segment {i}: {out_path}")
                return out_path
            except Exception as e:
                logger.warning(f"TTS segment {i} failed: {e} — using silence")
                out_path = os.path.join(output_dir, f"seg_{i:03d}.mp3")
                self._write_silent_mp3(out_path, duration=2.0)
                return out_path

        results = {}
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(_synth_one, i, text): i for i, text in tasks}
            for fut in futures:
                results[futures[fut]] = fut.result()
        return [results[i] for i, _ in tasks]

    def _write_silent_mp3(self, path: str, duration: float = 2.0) -> None:
        """Write a silent MP3 file of given duration in seconds."""
        try:
            ffmpeg = _get_ffmpeg()
            cmd = [
                ffmpeg, "-y",
                "-f", "lavfi",
                "-i", "anullsrc=r=22050:cl=mono",
                "-t", str(duration),
                "-q:a", "9",
                "-acodec", "libmp3lame",
                path,
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=10)
        except Exception as e:
            logger.warning(f"ffmpeg silence generation failed ({e}), using WAV fallback")
            _write_silent_wav(path, duration)


def _get_ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _is_wav(data: bytes) -> bool:
    return data[:4] == b"RIFF" and data[8:12] == b"WAVE"


def _write_silent_wav(path: str, duration: float) -> None:
    sample_rate = 22050
    num_samples = int(sample_rate * duration)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)
