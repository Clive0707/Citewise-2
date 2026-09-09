"""
Mistral LLM Provider
"""
import logging
import os
from typing import List, Dict, Optional

from mistralai import Mistral

from ..base import BaseLLMProvider
from ..rate_limiter import get_rate_limiter
from ...constants import MISTRAL_API_KEY_ENV, MODEL_MISTRAL_MEDIUM_LATEST

logger = logging.getLogger(__name__)


class MistralProvider(BaseLLMProvider):
    """Mistral LLM provider using Mistral AI SDK."""

    def __init__(self):
        self.api_key = os.getenv(MISTRAL_API_KEY_ENV)
        if not self.api_key:
            raise ValueError(f"{MISTRAL_API_KEY_ENV} environment variable must be set")
        
        self.model_name = MODEL_MISTRAL_MEDIUM_LATEST
        self.client = Mistral(api_key=self.api_key)
        self.rate_limiter = get_rate_limiter()
        logger.info(f"Initialized Mistral provider (model: {self.model_name})")

    async def wait_for_slot(self) -> None:
        """Wait for rate limit slot."""
        await self.rate_limiter.wait_for_slot(self.model_name)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send chat request to Mistral API.
        On any error, immediately raise exception to trigger next model in multi-provider.
        """
        try:
            # Wait for rate limit slot
            await self.wait_for_slot()

            # Convert messages to Mistral format
            mistral_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # Mistral uses "user" and "assistant" roles
                if role == "system":
                    # Mistral supports system messages, but we'll prepend to first user message if needed
                    if mistral_messages and mistral_messages[-1].get("role") == "user":
                        mistral_messages[-1]["content"] = f"{content}\n\n{mistral_messages[-1]['content']}"
                    else:
                        mistral_messages.append({"role": "user", "content": content})
                elif role in ["user", "assistant"]:
                    mistral_messages.append({"role": role, "content": content})
                elif role == "model":
                    # Gemini uses "model", convert to "assistant"
                    mistral_messages.append({"role": "assistant", "content": content})

            # Prepare chat completion parameters
            chat_params = {
                "model": self.model_name,
                "messages": mistral_messages,
            }
            
            if max_tokens is not None:
                chat_params["max_tokens"] = max_tokens
            if temperature is not None:
                chat_params["temperature"] = temperature

            # Generate content
            chat_response = self.client.chat.complete(**chat_params)

            if chat_response.choices and len(chat_response.choices) > 0:
                content = chat_response.choices[0].message.content
                if content:
                    return content.strip()
                else:
                    logger.warning(f"Mistral returned empty response for model {self.model_name}")
                    return ""
            else:
                logger.warning(f"Mistral returned no choices for model {self.model_name}")
                return ""

        except Exception as exc:
            # On any error, immediately raise to trigger next model in multi-provider
            error_str = str(exc)
            status_code = getattr(exc, 'status_code', None)
            
            # Log the error
            if status_code == 429 or "429" in error_str or "rate limit" in error_str.lower() or "quota" in error_str.lower():
                logger.warning(f"Mistral rate limit error (429): {exc}")
            elif status_code == 503 or "503" in error_str or "unavailable" in error_str.lower():
                logger.warning(f"Mistral server unavailable (503): {exc}")
            elif status_code == 401 or "401" in error_str or "unauthorized" in error_str.lower() or "invalid" in error_str.lower():
                logger.warning(f"Mistral authentication error (401): {exc}")
            else:
                logger.error(f"Mistral API error: {exc}")
            
            # Raise immediately to trigger next model
            raise

    def get_provider_name(self) -> str:
        return "Mistral"

