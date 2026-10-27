"""tests/test_bilingual.py — bilingual script text parsing (no LLM call)."""

from bilingual import _parse, _fallback


def test_parse_extracts_titles_and_segments():
    text = (
        "ENGLISH_TITLE: Carlsen vs Nepo\n"
        "HINDI_TITLE: कार्लसन बनाम नेपो\n"
        "ENGLISH:\n"
        "White opens strongly.\n"
        "Black responds solidly.\n"
        "HINDI:\n"
        "सफेद मजबूत शुरुआत करता है।\n"
    )
    script = _parse(text, "Carlsen", "Nepo", "Ruy Lopez")

    assert script.en_title == "Carlsen vs Nepo"
    assert script.hi_title == "कार्लसन बनाम नेपो"
    assert script.en_segments == ["White opens strongly.", "Black responds solidly."]
    assert script.hi_segments == ["सफेद मजबूत शुरुआत करता है।"]
    assert "ruy lopez" in script.hi_tags


def test_parse_missing_titles_falls_back_to_names():
    text = "ENGLISH:\nSome commentary.\n"
    script = _parse(text, "Alice", "Bob", "")

    assert script.en_title == "Alice vs Bob"
    assert "Alice" in script.hi_title and "Bob" in script.hi_title


def test_parse_no_sections_keeps_whole_text_as_english():
    script = _parse("just some raw unlabeled text", "Alice", "Bob", "")
    assert script.en_segments == ["just some raw unlabeled text"]
    assert script.hi_segments == []


def test_fallback_produces_hindi_segments_without_llm():
    script = _fallback("Alice", "Bob", "1-0", "Sicilian Defense")

    assert script.en_title == "Alice vs Bob"
    assert len(script.hi_segments) == 4
    assert "chess" in script.hi_tags
    assert "sicilian defense" in script.hi_tags
