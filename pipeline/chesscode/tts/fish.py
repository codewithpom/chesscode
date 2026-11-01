"""Fish's ElevenLabs-compatible timestamps preserve the existing caption pipeline."""
import base64
import os
import time
from pathlib import Path
from urllib.parse import quote

import requests

from .base import Word
from .elevenlabs import chars_to_words

MODEL = "s2.1-pro-free"


def check_access() -> None:
    response = requests.get(
        "https://api.fish.audio/wallet/self/api-credit",
        headers={"Authorization": f"Bearer {os.environ['FISH_API_KEY']}"}, timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Fish Audio authentication failed: HTTP {response.status_code}")


def synthesize(text: str, voice: str, lang: str, out_mp3: Path) -> list[Word]:
    try:
        for attempt in range(5):
            response = requests.post(
                f"https://api.fish.audio/compat/elevenlabs/v1/text-to-speech/{quote(voice, safe='')}/with-timestamps",
                headers={"xi-api-key": os.environ["FISH_API_KEY"], "model": MODEL},
                json={"text": text, "model_id": f"fish-audio/{MODEL}"},
                timeout=(15, 240),
            )
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            break
        result = response.json()
        alignment = result.get("alignment") or result["normalized_alignment"]
        chars, starts, ends = (alignment[k] for k in (
            "characters", "character_start_times_seconds", "character_end_times_seconds"))
        if not chars or not len(chars) == len(starts) == len(ends):
            raise ValueError("incomplete alignment")
        # shortcut: compatibility character timings interpolate native segments; use native word timestamps if drift appears.
        words = chars_to_words(chars, starts, ends)
        if not words or any(w["start_ms"] < 0 or w["end_ms"] < w["start_ms"] for w in words):
            raise ValueError("invalid word timings")
        if any(a["start_ms"] > b["start_ms"] for a, b in zip(words, words[1:])):
            raise ValueError("unordered word timings")
        audio = base64.b64decode(result["audio_base64"], validate=True)
        if not audio:
            raise ValueError("empty audio")
        out_mp3.parent.mkdir(parents=True, exist_ok=True)
        out_mp3.write_bytes(audio)
        return words
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", "unknown")
        raise RuntimeError(f"Fish Audio failed: HTTP {status}") from None
    except Exception:
        raise RuntimeError("Fish Audio synthesis or timestamp validation failed") from None
