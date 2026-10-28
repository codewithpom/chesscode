import os
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg

from chesscode.tts import align
from chesscode.tts.base import Word


def synthesize(text: str, voice: str, lang: str, out_mp3: Path) -> list[Word]:
    import numpy as np
    from kokoro_onnx import Kokoro

    kokoro = Kokoro(os.environ["KOKORO_MODEL"], os.environ["KOKORO_VOICES"])
    language = "hi" if lang == "hi" else "en-us"
    phonemes = kokoro.tokenizer.phonemize(text, language)
    samples, sample_rate = kokoro.create(phonemes, voice=voice, lang=language, speed=1.0, is_phonemes=True)
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    wav_path = out_mp3.with_suffix(".wav")
    with wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes((np.asarray(samples) * 32767).astype(np.int16).tobytes())
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(wav_path), str(out_mp3)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wav_path.unlink()
    return align.align_words(out_mp3, text, lang)
