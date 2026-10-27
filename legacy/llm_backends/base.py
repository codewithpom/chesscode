"""Base class for LLM backends.

All LLM backends must inherit from LLMBackend and implement the generate method.
"""

from abc import ABC, abstractmethod

__all__ = ["LLMBackend"]


class LLMBackend(ABC):
    """Abstract base for large language model backends."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
    ) -> str:
        """Generate text using the LLM.
        
        Args:
            system_prompt: System context/instructions
            user_prompt: User's request/prompt
            max_tokens: Maximum tokens in response
        
        Returns:
            Generated text response
        """
        ...
