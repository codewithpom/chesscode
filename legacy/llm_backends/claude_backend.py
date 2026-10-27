import anthropic
from .base import LLMBackend

class ClaudeBackend(LLMBackend):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20250514"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return msg.content[0].text
