import requests
from .base import TTSBackend

class ElevenLabsBackend(TTSBackend):
    def __init__(self, api_key: str, voice_en: str, voice_hi: str = ""):
        self._api_key = api_key
        self._voice_en = voice_en
        self._voice_hi = voice_hi or voice_en

    def synthesize(self, text: str, language: str = "en", speed: float = 1.0) -> bytes:
        voice_id = self._voice_hi if language == "hi" else self._voice_en
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": self._api_key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content
