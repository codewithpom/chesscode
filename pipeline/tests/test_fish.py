import base64
from unittest.mock import Mock

import pytest
import requests

from chesscode import tts
from chesscode.tts import fish


def response(status=200, text="Hello rook"):
    result = Mock(status_code=status, ok=status == 200)
    result.json.return_value = {
        "audio_base64": base64.b64encode(b"audio").decode(),
        "alignment": {"characters": list(text),
                      "character_start_times_seconds": [i / 10 for i in range(len(text))],
                      "character_end_times_seconds": [(i + 1) / 10 for i in range(len(text))]},
    }
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(response=result)
    return result


def test_free_model_and_hindi_timestamps(monkeypatch, tmp_path):
    monkeypatch.setenv("FISH_API_KEY", "sentinel-secret")
    post = Mock(return_value=response(text="rook गया"))
    monkeypatch.setattr(fish.requests, "post", post)
    words = fish.synthesize("rook गया", "voice", "hi", tmp_path / "speech.mp3")
    assert [w["w"] for w in words] == ["rook", "गया"]
    assert words[1]["start_ms"] == 500 and words[1]["end_ms"] == 800
    assert (tmp_path / "speech.mp3").read_bytes() == b"audio"
    assert post.call_args.kwargs["headers"]["model"] == "s2.1-pro-free"
    assert post.call_args.kwargs["json"] == {"text": "rook गया", "model_id": "fish-audio/s2.1-pro-free"}
    assert post.call_args.args[0].startswith("https://api.fish.audio/")
    assert tts.PROVIDERS["fish"] is fish.synthesize


def test_rate_limit_retries_without_falling_back_to_paid_model(monkeypatch, tmp_path):
    monkeypatch.setenv("FISH_API_KEY", "sentinel-secret")
    post = Mock(side_effect=[response(429), response(503), response()])
    monkeypatch.setattr(fish.requests, "post", post)
    sleep = Mock()
    monkeypatch.setattr(fish.time, "sleep", sleep)
    fish.synthesize("Hello rook", "voice", "en", tmp_path / "speech.mp3")
    assert [c.args[0] for c in sleep.call_args_list] == [1, 2]
    assert all(c.kwargs["json"]["model_id"] == "fish-audio/s2.1-pro-free" for c in post.call_args_list)


@pytest.mark.parametrize("status", [401, 402, 429])
def test_failed_auth_or_exhausted_retries_never_write_audio(monkeypatch, tmp_path, status):
    monkeypatch.setenv("FISH_API_KEY", "sentinel-secret")
    post = Mock(return_value=response(status))
    monkeypatch.setattr(fish.requests, "post", post)
    monkeypatch.setattr(fish.time, "sleep", Mock())
    with pytest.raises(RuntimeError, match=f"HTTP {status}") as error:
        fish.synthesize("Hello rook", "voice", "en", tmp_path / "speech.mp3")
    assert "sentinel-secret" not in str(error.value)
    assert post.call_count == (5 if status == 429 else 1)
    assert not (tmp_path / "speech.mp3").exists()


def test_bad_alignment_is_not_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("FISH_API_KEY", "sentinel-secret")
    result = response()
    result.json.return_value["alignment"]["character_end_times_seconds"] = []
    monkeypatch.setattr(fish.requests, "post", Mock(return_value=result))
    with pytest.raises(RuntimeError, match="timestamp validation"):
        fish.synthesize("Hello rook", "voice", "en", tmp_path / "speech.mp3")
    assert not (tmp_path / "speech.mp3").exists()


def test_zero_duration_function_word_from_real_fish_alignment_is_valid(monkeypatch, tmp_path):
    monkeypatch.setenv("FISH_API_KEY", "sentinel-secret")
    result = response(text="a rook")
    result.json.return_value["alignment"]["character_end_times_seconds"][0] = 0
    monkeypatch.setattr(fish.requests, "post", Mock(return_value=result))
    words = fish.synthesize("a rook", "voice", "en", tmp_path / "speech.mp3")
    assert words[0] == {"w": "a", "start_ms": 0, "end_ms": 0}
    assert len(words) == 2 and (tmp_path / "speech.mp3").exists()


def test_network_error_hides_key(monkeypatch, tmp_path):
    monkeypatch.setenv("FISH_API_KEY", "sentinel-secret")
    monkeypatch.setattr(fish.requests, "post", Mock(side_effect=RuntimeError("sentinel-secret")))
    with pytest.raises(RuntimeError) as error:
        fish.synthesize("Hello rook", "voice", "en", tmp_path / "speech.mp3")
    assert "sentinel-secret" not in str(error.value)


def test_zero_credit_balance_does_not_block_free_model(monkeypatch):
    monkeypatch.setenv("FISH_API_KEY", "sentinel-secret")
    get = Mock(return_value=response())
    monkeypatch.setattr(fish.requests, "get", get)
    assert fish.check_access() is None
    assert get.call_args.args[0] == "https://api.fish.audio/wallet/self/api-credit"
