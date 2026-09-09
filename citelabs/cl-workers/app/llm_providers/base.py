"""
Base LLM Provider Interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send a chat request to the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider."""
        pass

    @abstractmethod
    async def wait_for_slot(self) -> None:
        """
        Wait for a rate limit slot to become available.
        Uses the model name stored in the provider instance.
        """
        pass

