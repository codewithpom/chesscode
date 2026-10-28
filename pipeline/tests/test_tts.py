import json
import sys
from datetime import timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
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
    text = "घोड़ा फँस गया"
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


def test_azure_boundary_handles_timedelta(monkeypatch, tmp_path):
    instances = []
    class Signal:
        def connect(self, callback): self.callback = callback
    class Synth:
        def __init__(self, **kwargs):
            self.synthesis_word_boundary = Signal()
            instances.append(self)
        def speak_text_async(self, text):
            return SimpleNamespace(get=lambda: SimpleNamespace(reason="done", audio_data=b"mp3"))
    speech = ModuleType("azure.cognitiveservices.speech")
    speech.SpeechConfig = lambda **kwargs: SimpleNamespace(set_speech_synthesis_output_format=lambda _: None)
    speech.SpeechSynthesisOutputFormat = SimpleNamespace(Audio24Khz48KBitRateMonoMp3=1)
    speech.SpeechSynthesizer = Synth
    speech.ResultReason = SimpleNamespace(SynthesizingAudioCompleted="done")
    speech.SpeechSynthesisBoundaryType = SimpleNamespace(Word=1, Punctuation=2, Sentence=3)
    parent, child = ModuleType("azure"), ModuleType("azure.cognitiveservices")
    parent.cognitiveservices = child
    child.speech = speech
    for name, module in (("azure", parent), ("azure.cognitiveservices", child),
                         ("azure.cognitiveservices.speech", speech)):
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "region")
    words = tts.azure.synthesize("hello", "voice", "en", tmp_path / "out.mp3")
    callback = instances[0].synthesis_word_boundary.callback
    callback(SimpleNamespace(boundary_type=1, text="hello", audio_offset=20_000,
                              duration=timedelta(milliseconds=125)))
    callback(SimpleNamespace(boundary_type=2, text=",", audio_offset=0,
                              duration=timedelta(milliseconds=1)))
    assert words == [{"w": "hello", "start_ms": 2, "end_ms": 127}]


def test_synthesize_rejects_empty_timings_and_keeps_raw_on_normalize_failure(tmp_path):
    with patch.dict(tts.PROVIDERS, {"empty": Mock(return_value=[])}), patch.object(audio, "loudnorm"):
        try:
            tts.synthesize("empty", "hello", "voice", "en", tmp_path)
        except RuntimeError as exc:
            assert "word timing" in str(exc)
        else:
            raise AssertionError("empty timing list was accepted")
    assert not list(tmp_path.glob("*.words.json"))
    def provide(text, voice, lang, path):
        path.write_bytes(b"raw")
        return [{"w": "hello", "start_ms": 0, "end_ms": 1}]
    provider = Mock(side_effect=provide)
    with patch.dict(tts.PROVIDERS, {"raw": provider}), patch.object(audio, "loudnorm", side_effect=OSError):
        try:
            tts.synthesize("raw", "hello", "voice", "en", tmp_path)
        except OSError:
            pass
    assert list(tmp_path.glob("*.raw.mp3"))
    def normalize(raw, dst):
        dst.write_bytes(b"normalized")
    with patch.dict(tts.PROVIDERS, {"raw": Mock(side_effect=AssertionError("raw cache should avoid provider"))}), \
         patch.object(audio, "loudnorm", side_effect=normalize):
        output, words = tts.synthesize("raw", "hello", "voice", "en", tmp_path)
    assert output.exists() and words[0]["w"] == "hello"
    provider.assert_called_once()


def test_alignment_uses_known_text_and_interpolates_missing_timestamps(monkeypatch, tmp_path):
    align_calls = {}
    fake = ModuleType("whisperx")
    fake.load_audio = lambda _: [0.0] * 32_000
    fake.load_align_model = lambda **kwargs: (object(), {})
    def align(segments, *args):
        align_calls["segments"] = segments
        return {"word_segments": [{"word": "Nf3"}, {"word": "wins", "start": 1.0, "end": 1.5}]}
    fake.align = align
    monkeypatch.setitem(sys.modules, "whisperx", fake)
    words = tts.align.align_words(tmp_path / "audio.mp3", "Nf3 wins", "en")
    assert align_calls["segments"][0]["text"] == "Nf3 wins"
    assert words[0]["start_ms"] >= 0 and words[0]["end_ms"] > words[0]["start_ms"]


def test_elevenlabs_uses_original_alignment_and_reports_status(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "secret")
    response = Mock()
    response.json.return_value = {"audio_base64": "YWJj", "alignment": {
        "characters": list("abc"), "character_start_times_seconds": [0, .1, .2],
        "character_end_times_seconds": [.1, .2, .3]}, "normalized_alignment": {"characters": list("normalized")}}
    with patch.object(tts.elevenlabs.requests, "post", return_value=response):
        words = tts.elevenlabs.synthesize("abc", "voice", "en", tmp_path / "a.mp3")
    assert words[0]["w"] == "abc"
    response.raise_for_status.side_effect = tts.elevenlabs.requests.HTTPError(
        response=SimpleNamespace(status_code=429))
    with patch.object(tts.elevenlabs.requests, "post", return_value=response):
        try:
            tts.elevenlabs.synthesize("abc", "voice", "en", tmp_path / "b.mp3")
        except RuntimeError as exc:
            assert "HTTP 429" in str(exc) and "secret" not in str(exc)
        else:
            raise AssertionError("HTTP error was hidden")


def test_elevenlabs_chunks_requests_at_provider_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "secret")
    response = Mock()
    response.json.return_value = {"audio_base64": "YWJj", "alignment": {
        "characters": ["a"], "character_start_times_seconds": [0],
        "character_end_times_seconds": [.1]}}
    with patch.object(tts.elevenlabs.requests, "post", return_value=response) as post:
        tts.elevenlabs.synthesize("x" * 10_001, "voice", "en", tmp_path / "long.mp3")
    assert post.call_count == 2
    assert max(len(call.kwargs["json"]["text"]) for call in post.call_args_list) <= 10_000
