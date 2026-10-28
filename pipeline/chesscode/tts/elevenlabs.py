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
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= 10_000:
            chunks.append(remaining)
            break
        split_at = remaining.rfind(" ", 0, 10_001)
        if split_at < 1:
            split_at = 10_000
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()
    audio = bytearray()
    words = []
    offset = 0
    try:
        for chunk in chunks:
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps",
                headers={"xi-api-key": key, "Content-Type": "application/json"},
                json={"text": chunk, "model_id": "eleven_multilingual_v2"}, timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            alignment = result.get("alignment") or result["normalized_alignment"]
            chunk_words = chars_to_words(alignment["characters"], alignment["character_start_times_seconds"],
                                         alignment["character_end_times_seconds"])
            words.extend({**word, "start_ms": word["start_ms"] + offset,
                          "end_ms": word["end_ms"] + offset} for word in chunk_words)
            if alignment["character_end_times_seconds"]:
                offset += round(max(alignment["character_end_times_seconds"]) * 1000)
            audio.extend(base64.b64decode(result["audio_base64"]))
        out_mp3.parent.mkdir(parents=True, exist_ok=True)
        out_mp3.write_bytes(audio)
        return words
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", "unknown")
        raise RuntimeError(f"ElevenLabs failed: HTTP {status}") from None
    except Exception:
        raise RuntimeError("ElevenLabs synthesis failed") from None
