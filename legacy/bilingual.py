"""bilingual.py — Bilingual (English + Hindi) chess script generation."""

import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class BilingualScript:
    en_title: str = ""
    hi_title: str = ""
    en_description: str = ""
    hi_description: str = ""
    en_segments: List[str] = field(default_factory=list)
    hi_segments: List[str] = field(default_factory=list)
    hi_tags: List[str] = field(default_factory=list)


class BilingualScriptGenerator:
    _SYSTEM = (
        "You are a bilingual chess content creator for YouTube. "
        "Write TWO independent scripts for the same game — one in English, one in Hindi. "
        "The Hindi script must use natural Devanagari — not translated English. "
        "Use Hindi chess idioms, cultural phrases, and commentary style native to "
        "Hindi-speaking audiences. Each script has its own pacing and emotion. "
        "Hindi must feel like a native Hindi commentator, not a translator."
    )

    def __init__(self):
        from config import cfg
        from llm_backends import get_backend
        self._backend = get_backend(cfg)

    def generate(self, analysis, game_pgn=None) -> BilingualScript:
        white   = getattr(analysis, "white", "White")
        black   = getattr(analysis, "black", "Black")
        result  = getattr(analysis, "result", "*")
        opening = getattr(analysis, "opening", "")

        prompt = (
            f"Create two independent scripts for: {white} vs {black} ({result}).\n"
            f"Opening: {opening}\n\n"
            "Write SEPARATE scripts with their own voice and energy — not translations.\n\n"
            "Provide exactly:\n"
            "ENGLISH_TITLE: <title>\n"
            "HINDI_TITLE: <Hindi title in Devanagari>\n"
            "ENGLISH:\n<3-5 engaging commentary sentences for English YouTube audience>\n"
            "HINDI:\n<3-5 sentences in Devanagari Hindi for Hindi YouTube audience — "
            "use Hindi chess idioms and native commentary style, NOT a translation>"
        )

        try:
            resp = self._backend.generate(
                system_prompt=self._SYSTEM,
                user_prompt=prompt,
                max_tokens=700,
            )
            return _parse(resp, white, black, opening)
        except Exception as e:
            logger.warning(f"Bilingual LLM call failed ({e}), using fallback")
            return _fallback(white, black, result, opening)


def _parse(text: str, white: str, black: str, opening: str) -> BilingualScript:
    en_title = hi_title = ""
    en_lines: List[str] = []
    hi_lines: List[str] = []
    section = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("ENGLISH_TITLE:"):
            en_title = line.split(":", 1)[1].strip()
        elif line.upper().startswith("HINDI_TITLE:"):
            hi_title = line.split(":", 1)[1].strip()
        elif line.upper().startswith("ENGLISH:"):
            section = "en"
            rest = line.split(":", 1)[1].strip()
            if rest:
                en_lines.append(rest)
        elif line.upper().startswith("HINDI:"):
            section = "hi"
            rest = line.split(":", 1)[1].strip()
            if rest:
                hi_lines.append(rest)
        elif section == "en":
            en_lines.append(line)
        elif section == "hi":
            hi_lines.append(line)

    return BilingualScript(
        en_title=en_title or f"{white} vs {black}",
        hi_title=hi_title or f"{white} बनाम {black}",
        en_segments=en_lines or [text],
        hi_segments=hi_lines,
        hi_tags=["chess", "शतरंज", opening.lower()],
    )


def _fallback(white: str, black: str, result: str, opening: str) -> BilingualScript:
    hi_segs = [
        f"ChessCode में आपका स्वागत है! आज {white} बनाम {black} का खेल देखते हैं।",
        f"इस खेल में {opening} का उपयोग हुआ।",
        f"खेल का परिणाम: {result}",
        "ChessCode पर और भी शतरंज विश्लेषण देखें!",
    ]
    return BilingualScript(
        en_title=f"{white} vs {black}",
        hi_title=f"{white} बनाम {black}",
        hi_segments=hi_segs,
        hi_tags=["chess", "शतरंज", "chesscode", opening.lower()],
    )
