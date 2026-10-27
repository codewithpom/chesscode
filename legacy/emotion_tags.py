"""emotion_tags.py — Free/local emotion cue for narration text.

Kokoro has no emotion parameter, only voice + speed. This lets narration
scripts embed a single leading tag like "[excited] White crushes..." which
gets stripped before synthesis and mapped to a speed multiplier so the line
reads faster/slower/punchier without any paid API.
"""

import re

# Tag -> speed multiplier. Tune by ear; Kokoro's speed range is roughly 0.5-1.5.
EMOTION_SPEED = {
    "excited":   1.15,
    "urgent":    1.2,
    "dramatic":  0.85,
    "calm":      0.9,
    "sad":       0.85,
    "whisper":   0.9,
    "neutral":   1.0,
}

_TAG_RE = re.compile(r"^\s*\[([a-zA-Z]+)\]\s*")


def parse_emotion(text: str) -> tuple[str, float]:
    """Strip a leading [tag] from text, return (clean_text, speed).

    Unknown or missing tags default to speed 1.0.
    """
    m = _TAG_RE.match(text)
    if not m:
        return text, 1.0
    tag = m.group(1).lower()
    speed = EMOTION_SPEED.get(tag, 1.0)
    return text[m.end():], speed
