import httpx
from .base import LLMBackend

class OllamaBackend(LLMBackend):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self._base_url = base_url.rstrip("/")
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        resp = httpx.post(
            f"{self._base_url}/v1/chat/completions",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "stream": False,
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
