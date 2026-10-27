"""tests/test_config.py — env parsing + computed properties on ChessCodeConfig."""

from config import ChessCodeConfig


def test_canvas_size_splits_resolution():
    c = ChessCodeConfig(resolution="1920x1080")
    assert c.canvas_size == (1920, 1080)


def test_active_tts_backend_kokoro():
    c = ChessCodeConfig(tts_backend="kokoro")
    assert c.active_tts_backend == "kokoro"


def test_active_tts_backend_elevenlabs_requires_key():
    c = ChessCodeConfig(tts_backend="elevenlabs", elevenlabs_api_key="")
    assert c.active_tts_backend == "gtts"  # no key -> falls back

    c = ChessCodeConfig(tts_backend="elevenlabs", elevenlabs_api_key="sk-123")
    assert c.active_tts_backend == "elevenlabs"


def test_active_tts_backend_unknown_falls_back_to_gtts():
    c = ChessCodeConfig(tts_backend="something_else")
    assert c.active_tts_backend == "gtts"


def test_has_properties_reflect_keys():
    c = ChessCodeConfig(anthropic_api_key="", leonardo_api_key="k", lichess_token="")
    assert c.has_anthropic is False
    assert c.has_leonardo is True
    assert c.has_lichess is False


def test_has_ollama_reflects_backend_choice():
    assert ChessCodeConfig(llm_backend="ollama").has_ollama is True
    assert ChessCodeConfig(llm_backend="claude").has_ollama is False


def test_has_youtube_data_api_requires_both():
    assert ChessCodeConfig(youtube_api_key="", youtube_channel_id="UC1").has_youtube_data_api is False
    assert ChessCodeConfig(youtube_api_key="k", youtube_channel_id="").has_youtube_data_api is False
    assert ChessCodeConfig(youtube_api_key="k", youtube_channel_id="UC1").has_youtube_data_api is True
