"""move_sfx.py — Per-move sound effects (move, capture, check, checkmate, castle).
Uses real sounds from the Lichess "sfx" set (open source, public domain) decoded to
raw PCM in assets/sfx/pcm/. Falls back to synthesized tones if those files are
missing (e.g. a fresh checkout that hasn't fetched them yet).
"""

import os
import numpy as np

_SR = 44100
_PCM_DIR = os.path.join(os.path.dirname(__file__), "assets", "sfx", "pcm")
_REAL_FILES = {
    "move": "Move.pcm",
    "capture": "Capture.pcm",
    "check": "Check.pcm",
    "checkmate": "Checkmate.pcm",
    "castle": "Move.pcm",  # lichess has no dedicated castle sound either
}


def classify_san(san: str) -> str:
    """Classify a SAN move string into a sound-effect category."""
    if not san:
        return "move"
    if "#" in san:
        return "checkmate"
    if "+" in san:
        return "check"
    if san.startswith("O-O"):
        return "castle"
    if "x" in san:
        return "capture"
    return "move"


def _tone(freq: float, dur: float, amp: float = 0.4, decay: float = 10.0,
          sr: int = _SR) -> np.ndarray:
    n = int(sr * dur)
    t = np.arange(n) / sr
    env = np.exp(-decay * t)
    wave = np.sin(2 * np.pi * freq * t) * env * amp
    return wave


def _click(dur: float, amp: float = 0.5, decay: float = 40.0, sr: int = _SR) -> np.ndarray:
    n = int(sr * dur)
    t = np.arange(n) / sr
    env = np.exp(-decay * t)
    noise = np.random.default_rng(0).uniform(-1, 1, n)
    return noise * env * amp


def _seq(*parts: np.ndarray, gap: float = 0.03, sr: int = _SR) -> np.ndarray:
    gap_n = int(sr * gap)
    pieces = []
    for i, p in enumerate(parts):
        pieces.append(p)
        if i < len(parts) - 1:
            pieces.append(np.zeros(gap_n))
    return np.concatenate(pieces) if pieces else np.zeros(0)


def _mix(*parts: np.ndarray) -> np.ndarray:
    n = max((len(p) for p in parts), default=0)
    out = np.zeros(n)
    for p in parts:
        out[:len(p)] += p
    return out


def _build(kind: str) -> np.ndarray:
    if kind == "move":
        return _click(0.07, amp=0.35, decay=55.0)
    if kind == "capture":
        return _mix(_click(0.09, amp=0.55, decay=35.0),
                    _tone(280, 0.10, amp=0.30, decay=25.0))
    if kind == "castle":
        return _seq(_click(0.06, amp=0.35, decay=55.0),
                    _click(0.06, amp=0.35, decay=55.0), gap=0.09)
    if kind == "check":
        return _seq(_tone(620, 0.09, amp=0.35, decay=25.0),
                    _tone(920, 0.11, amp=0.35, decay=20.0), gap=0.02)
    if kind == "checkmate":
        return _seq(_tone(900, 0.14, amp=0.45, decay=14.0),
                    _tone(700, 0.14, amp=0.45, decay=14.0),
                    _tone(480, 0.22, amp=0.45, decay=9.0), gap=0.01)
    return np.zeros(0)


_CACHE = {}


def get_sfx_pcm16(kind: str) -> bytes:
    """Return mono 16-bit PCM bytes (at 44100 Hz) for a move-type sound effect."""
    if kind in _CACHE:
        return _CACHE[kind]

    real_path = os.path.join(_PCM_DIR, _REAL_FILES.get(kind, ""))
    if _REAL_FILES.get(kind) and os.path.exists(real_path):
        with open(real_path, "rb") as f:
            data = f.read()
        _CACHE[kind] = data
        return data

    wave = _build(kind)
    clipped = np.clip(wave, -1.0, 1.0)
    _CACHE[kind] = (clipped * 32767).astype(np.int16).tobytes()
    return _CACHE[kind]
