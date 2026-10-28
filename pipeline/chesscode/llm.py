import json

import jsonschema

from .config import load
from .context import StageError

def complete_json(model_key: str, system: str, user: str, schema: dict, client=None, retries: int = 2) -> dict:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    models = load("models")
    model = models[model_key]
    for attempt in range(retries + 1):
        try:
            if hasattr(client, "complete"):
                raw = client.complete(model=model, system=system, user=user, schema=schema)
            else:
                response = client.messages.create(model=model, max_tokens=8192, system=system, messages=[{"role":"user","content":user}])
                raw = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        except Exception as exc:
            raise StageError("unknown", "script", f"model request failed: {exc}") from exc
        try:
            value = json.loads(raw) if isinstance(raw, str) else raw
            jsonschema.validate(value, schema)
            return value
        except (json.JSONDecodeError, jsonschema.ValidationError, TypeError) as exc:
            error = exc
    raise StageError("unknown", "script", f"invalid model JSON after {retries + 1} attempts: {error}") from error
