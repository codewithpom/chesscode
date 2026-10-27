from .base import LLMBackend
from .claude_backend import ClaudeBackend
from .ollama_backend import OllamaBackend


def get_backend(cfg) -> LLMBackend:
    """Return the configured LLM backend. cfg is a ChessCodeConfig instance."""
    if cfg.llm_backend == "ollama":
        return OllamaBackend(base_url=cfg.ollama_url, model=cfg.ollama_model)
    return ClaudeBackend(api_key=cfg.anthropic_api_key)


__all__ = ["LLMBackend", "ClaudeBackend", "OllamaBackend", "get_backend"]
