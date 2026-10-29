import hashlib
import json
import os
from pathlib import Path

import jsonschema

from .config import load
from .context import REPO_ROOT, StageError


class AnswerMissing(Exception):
    def __init__(self, request: Path):
        super().__init__(f"no answer yet; request written to {request}")
        self.request = request


class OfflineClient:
    """No API key: the stage writes each request to build/llm_requests/<key>.json and an agent outside the
    pipeline answers it in build/llm_answers/<key>.json; the stage is rerun until it passes. Only the final
    script (content/scripts/<video_id>.json) is committed, so batch runs never depend on these keys."""
    def __init__(self, root: Path = REPO_ROOT):
        self.root = root

    def complete(self, model: str, system: str, user: str, schema: dict):
        key = hashlib.sha256(json.dumps([model, system, user], ensure_ascii=False).encode("utf-8")).hexdigest()[:20]
        request = self.root / "build" / "llm_requests" / f"{key}.json"
        answer = self.root / "build" / "llm_answers" / f"{key}.json"
        if answer.is_file():
            try:
                value = json.loads(answer.read_text(encoding="utf-8-sig"))
                jsonschema.validate(value, schema)
            except (json.JSONDecodeError, jsonschema.ValidationError) as exc:
                raise StageError("unknown", "script", f"invalid answer {answer.relative_to(self.root).as_posix()} for request {request.name}: {exc}") from None
            request.unlink(missing_ok=True)
            return value
        request.parent.mkdir(parents=True, exist_ok=True)
        request.write_text(json.dumps({"key": key, "model": model, "answer_path": answer.relative_to(self.root).as_posix(), "system": system,
                                       "user": user, "schema": schema}, ensure_ascii=False, indent=2), encoding="utf-8")
        raise AnswerMissing(request)


def provider() -> str:
    """config/models.yaml `provider`: anthropic (needs ANTHROPIC_API_KEY), offline, or auto (anthropic when the key is set)."""
    name = load("models").get("provider", "auto")
    if name not in ("anthropic", "offline", "auto"):
        raise StageError("unknown", "script", f"config/models.yaml provider must be anthropic, offline or auto, not {name!r}")
    return "anthropic" if name == "anthropic" or (name == "auto" and os.getenv("ANTHROPIC_API_KEY")) else "offline"


def default_client():
    if provider() == "anthropic":
        import anthropic
        return anthropic.Anthropic()
    return OfflineClient()


def complete_json(model_key: str, system: str, user: str, schema: dict, client=None, retries: int = 2) -> dict:
    if client is None:
        client = default_client()
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
        except AnswerMissing as exc:
            raise StageError("unknown", "script", str(exc)) from None
        except Exception as exc:
            raise StageError("unknown", "script", f"model request failed: {exc}") from exc
        try:
            value = json.loads(raw) if isinstance(raw, str) else raw
            jsonschema.validate(value, schema)
            return value
        except (json.JSONDecodeError, jsonschema.ValidationError, TypeError) as exc:
            error = exc
    raise StageError("unknown", "script", f"invalid model JSON after {retries + 1} attempts: {error}") from error
