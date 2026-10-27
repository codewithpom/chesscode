import base64
import os
from pathlib import Path

import requests

from chesscode.tts.base import Word


def chars_to_words(chars: list[str], starts_s: list[float], ends_s: list[float]) -> list[Word]:
    words = []
    current = []
    for char, start, end in zip(chars, starts_s, ends_s):
        if char.isspace():
            if current:
                words.append({"w": "".join(item[0] for item in current), "start_ms": round(current[0][1] * 1000),
                              "end_ms": round(current[-1][2] * 1000)})
                current = []
        else:
            current.append((char, start, end))
    if current:
        words.append({"w": "".join(item[0] for item in current), "start_ms": round(current[0][1] * 1000),
                      "end_ms": round(current[-1][2] * 1000)})
    return words


def synthesize(text: str, voice: str, lang: str, out_mp3: Path) -> list[Word]:
    key = os.environ["ELEVENLABS_API_KEY"]
    try:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps",
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_multilingual_v2"}, timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        alignment = result.get("normalized_alignment") or result["alignment"]
        out_mp3.write_bytes(base64.b64decode(result["audio_base64"]))
        return chars_to_words(alignment["characters"], alignment["character_start_times_seconds"],
                              alignment["character_end_times_seconds"])
    except Exception:
        raise RuntimeError("ElevenLabs synthesis failed") from None
