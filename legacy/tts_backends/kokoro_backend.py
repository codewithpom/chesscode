import io
import re
import numpy as np
from .base import TTSBackend

# espeak emits two-letter language markers like "(hi)" or "(en)" into the phoneme
# stream on a language switch. Kokoro voices them literally (e.g. Hindi clips end
# up saying "hi"), so strip every such marker before synthesis.
_ESPEAK_LANG_TAG = re.compile(r"\([a-z]{2}\)")

class KokoroBackend(TTSBackend):
    def __init__(self, voice_en: str = "af_heart", voice_hi: str = "hf_alpha"):
        self._voice_en = voice_en
        self._voice_hi = voice_hi
        self._pipeline = None  # lazy load

    def _get_pipeline(self):
        if self._pipeline is None:
            import os
            from kokoro_onnx import Kokoro
            # Model files live in the project root alongside this package
            proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            onnx_path = os.path.join(proj, "kokoro-v1.0.onnx")
            voices_path = os.path.join(proj, "voices-v1.0.bin")
            self._pipeline = Kokoro(onnx_path, voices_path)
        return self._pipeline

    def synthesize(self, text: str, language: str = "en", speed: float = 1.0) -> bytes:
        voice = self._voice_hi if language == "hi" else self._voice_en
        lang_code = "hi" if language == "hi" else "en-us"
        pipeline = self._get_pipeline()
        phonemes = pipeline.tokenizer.phonemize(text, lang_code)
        phonemes = _ESPEAK_LANG_TAG.sub("", phonemes)
        samples, sample_rate = pipeline.create(phonemes, voice=voice, lang=lang_code,
                                               speed=speed, is_phonemes=True)
        return _samples_to_wav_bytes(samples, sample_rate)


def _samples_to_wav_bytes(samples: np.ndarray, sample_rate: int) -> bytes:
    import wave
    buf = io.BytesIO()
    samples_int16 = (samples * 32767).astype(np.int16)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples_int16.tobytes())
    buf.seek(0)
    return buf.read()
