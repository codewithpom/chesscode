import json
from pathlib import Path
from unittest.mock import Mock, patch

from chesscode import audio, tts
from chesscode.tts.base import Word


def test_chars_to_words_english():
    assert tts.elevenlabs.chars_to_words(list("Hi there"), [0, .1, .2, .3, .4, .5, .6, .7],
                                        [.1, .2, .3, .4, .5, .6, .7, .8]) == [
        {"w": "Hi", "start_ms": 0, "end_ms": 200},
        {"w": "there", "start_ms": 300, "end_ms": 800},
    ]


def test_chars_to_words_hindi_keeps_matras():
    text = "घोड़़ा फँस गया"
    words = tts.elevenlabs.chars_to_words(list(text), [i / 100 for i in range(len(text))],
                                          [(i + 1) / 100 for i in range(len(text))])
    assert [word["w"] for word in words] == text.split(" ")


def test_azure_ticks_to_ms():
    assert tts.azure.ticks_to_ms(10_000) == 1


def test_cache_hit_skips_provider(tmp_path):
    key = tts.cache_key("provider", "voice", "hello")
    (tmp_path / f"{key}.mp3").write_bytes(b"audio")
    (tmp_path / f"{key}.words.json").write_text(json.dumps([{"w": "hello", "start_ms": 0, "end_ms": 1}]))
    with patch.object(audio, "loudnorm") as normalize, patch.dict(tts.PROVIDERS, {"provider": Mock(side_effect=AssertionError)}):
        assert tts.synthesize("provider", "hello", "voice", "en", tmp_path) == (
            tmp_path / f"{key}.mp3", [{"w": "hello", "start_ms": 0, "end_ms": 1}])
    normalize.assert_not_called()


def test_cache_key_changes_with_voice():
    assert tts.cache_key("provider", "one", "hello") != tts.cache_key("provider", "two", "hello")


def test_provider_error_message_hides_key(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk-secret")
    with patch("chesscode.tts.elevenlabs.requests.post", side_effect=RuntimeError("request failed with sk-secret")):
        try:
            tts.elevenlabs.synthesize("hello", "voice", "en", tmp_path / "x.mp3")
        except RuntimeError as exc:
            assert "sk-secret" not in str(exc)
        else:
            raise AssertionError("provider error was not raised")
