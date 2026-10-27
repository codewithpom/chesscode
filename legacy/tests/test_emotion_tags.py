"""tests/test_emotion_tags.py — [tag] narration cue parsing for Kokoro TTS speed."""

from emotion_tags import parse_emotion


def test_known_tag_strips_and_maps_speed():
    text, speed = parse_emotion("[excited] White crushes the attack!")
    assert text == "White crushes the attack!"
    assert speed == 1.15


def test_unknown_tag_defaults_to_speed_one():
    text, speed = parse_emotion("[mysterious] A quiet position.")
    assert text == "A quiet position."
    assert speed == 1.0


def test_no_tag_returns_text_unchanged():
    text, speed = parse_emotion("Just plain narration.")
    assert text == "Just plain narration."
    assert speed == 1.0


def test_tag_is_case_insensitive():
    text, speed = parse_emotion("[EXCITED] Go!")
    assert speed == 1.15


def test_only_leading_tag_is_stripped():
    text, speed = parse_emotion("Not [excited] at the start")
    assert text == "Not [excited] at the start"
    assert speed == 1.0
