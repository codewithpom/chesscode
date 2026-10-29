import re

import pytest
import yaml

from conftest import REPO_ROOT

BEATS = yaml.safe_load((REPO_ROOT / "config" / "beats.yaml").read_text(encoding="utf-8"))["priority"]
LIMITS = {"en": 8, "hi": 10}  # same count as script.py::select_bank_line: len(line.split())
# Short blocklist (spec 8 rule 4): profanity, religion, politics, nationality, rating, dated memes.
BLOCK_WORDS = {"damn", "hell", "crap", "shit", "fuck", "bastard", "idiot", "stupid",
               "god", "gods", "jesus", "allah", "pray", "prayer", "omg", "bhagwan",
               "modi", "bjp", "congress", "election", "politics",
               "indian", "russian", "american", "chinese", "pakistani", "rating", "elo",
               "sus", "rizz", "lol"}
BLOCK_PHRASES = ["no cap", "skill issue", "it's giving", "भगवान", "अल्लाह", "ईश्वर", "साला", "कमीना", "बेवकूफ", "भारतीय", "रूसी"]


def bank(language):
    return yaml.safe_load((REPO_ROOT / "content" / "lines" / f"{language}.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("language", ["en", "hi"])
def test_bank_covers_beats_with_short_unique_clean_lines(language):
    lines = bank(language)
    assert set(BEATS) <= set(lines), f"missing beat types: {set(BEATS) - set(lines)}"
    every = []
    for beat in BEATS:
        assert len(lines[beat]) >= 25, f"{language}.{beat} has {len(lines[beat])} lines"
        for line in lines[beat]:
            assert isinstance(line, str) and line.strip(), f"{language}.{beat}: empty line"
            assert len(line.split()) <= LIMITS[language], f"{language}.{beat} too long: {line}"
            lower = line.lower()
            bad = (set(re.findall(r"[a-z']+", lower)) & BLOCK_WORDS) | {p for p in BLOCK_PHRASES if p in lower}
            assert not bad, f"{language}.{beat} blocklisted {bad}: {line}"
            if language == "hi":
                assert re.search(r"[ऀ-ॿ]", line), f"hi.{beat} has no Devanagari: {line}"
        every += lines[beat]
    dupes = {line for line in every if every.count(line) > 1}
    assert not dupes, f"{language} repeats lines: {dupes}"
