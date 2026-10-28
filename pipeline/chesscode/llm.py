import json

import jsonschema

from .config import load
from .context import StageError

def complete_json(model_key: str, system: str, user: str, schema: dict, client=None, retries: int = 2) -> dict:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    models = load("models")
    model = models[model_key]; max_tokens = models["max_tokens"][model_key]
    for attempt in range(retries + 1):
        try:
            if hasattr(client, "complete"):
                raw = client.complete(model=model, system=system, user=user, schema=schema)
            else:
                response = client.messages.create(model=model, max_tokens=max_tokens, system=system, messages=[{"role":"user","content":user}])
                if getattr(response, "stop_reason", None) == "max_tokens":  # a retry would truncate the same way
                    raise StageError("unknown", "script", f"model output was cut off at max_tokens {max_tokens}: raise max_tokens.{model_key} in config/models.yaml")
                raw = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        except StageError: raise
        except Exception as exc:
            raise StageError("unknown", "script", f"model request failed: {exc}") from exc
        try:
            value = json.loads(raw) if isinstance(raw, str) else raw
            jsonschema.validate(value, schema)
            return value
        except (json.JSONDecodeError, jsonschema.ValidationError, TypeError) as exc:
            error = exc
    raise StageError("unknown", "script", f"invalid model JSON after {retries + 1} attempts: {error}") from error
