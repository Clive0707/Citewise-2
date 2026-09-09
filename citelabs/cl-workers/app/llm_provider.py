"""
LLM Provider Abstraction Layer

This module provides a unified interface for different LLM backends.
Supports: Ollama (local), Gemini (cloud), and extensible for future providers.

Switch between providers using LLM_PROVIDER environment variable.
"""
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM implementations."""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: The input prompt/question
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider for logging."""
        pass


def get_llm_provider() -> LLMProvider:
    """
    Factory function to get the configured LLM provider.

    Returns the appropriate LLMProvider implementation based on
    LLM_PROVIDER environment variable.

    Returns:
        LLMProvider: Configured LLM provider instance

    Environment Variables:
        LLM_PROVIDER: "ollama" (default) or "gemini"
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "gemini":
        logger.info("Using Gemini LLM provider")
        from .llm_gemini import GeminiLLMProvider

        return GeminiLLMProvider()
    elif provider == "ollama":
        logger.info("Using Ollama LLM provider (local)")
        from .llm_ollama import OllamaLLMProvider

        return OllamaLLMProvider()
    else:
        logger.warning(
            f"Unknown LLM_PROVIDER '{provider}', defaulting to Ollama"
        )
        from .llm_ollama import OllamaLLMProvider

        return OllamaLLMProvider()




