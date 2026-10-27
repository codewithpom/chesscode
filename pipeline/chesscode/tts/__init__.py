import hashlib
import json
from pathlib import Path

from chesscode import audio
from chesscode.tts import azure, elevenlabs, kokoro
from chesscode.tts.base import Synth, Word

PROVIDERS: dict[str, Synth] = {
    "elevenlabs": elevenlabs.synthesize,
    "azure": azure.synthesize,
    "kokoro": kokoro.synthesize,
}


def cache_key(provider: str, voice: str, text: str) -> str:
    return hashlib.sha256(json.dumps((provider, voice, text), ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def synthesize(provider: str, text: str, voice: str, lang: str,
               cache_dir: Path) -> tuple[Path, list[Word]]:
    key = cache_key(provider, voice, text)
    output = cache_dir / f"{key}.mp3"
    words_path = cache_dir / f"{key}.words.json"
    if output.exists() and words_path.exists():
        return output, json.loads(words_path.read_text(encoding="utf-8"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    raw = cache_dir / f"{key}.raw.mp3"
    words = PROVIDERS[provider](text, voice, lang, raw)
    audio.loudnorm(raw, output)
    raw.unlink(missing_ok=True)
    words_path.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    return output, words
