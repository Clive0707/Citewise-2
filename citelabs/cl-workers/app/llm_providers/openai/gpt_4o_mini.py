"""
GPT 4o Mini LLM Provider with Rate Limiting (OpenAI Responses API)
"""
import asyncio
import logging
import os
from typing import List, Dict, Optional
import httpx

from ..base import BaseLLMProvider
from ..rate_limiter import get_rate_limiter
from ...constants import MODEL_GPT_4_O_MINI

logger = logging.getLogger(__name__)


class GPT4oMiniProvider(BaseLLMProvider):
    """OpenAI GPT 4o Mini provider using the Responses API."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be set")
        
        # Log masked API key for debugging (show first 7 chars and last 4 chars)
        masked_key = self._mask_api_key(self.api_key)
        logger.info(f"[OPENAI_API_KEY] Using API key: {masked_key} (length: {len(self.api_key)})")
        
        self.base_url = "https://api.openai.com/v1"
        self.model_name = MODEL_GPT_4_O_MINI
        self.rate_limiter = get_rate_limiter()
        logger.info(f"Initialized GPT 4o Mini provider (model: {self.model_name})")
    
    @staticmethod
    def _mask_api_key(api_key: str) -> str:
        """Mask API key for safe logging (show first 7 and last 4 characters)."""
        if not api_key or len(api_key) < 11:
            return "***"  # Too short to mask safely
        return f"{api_key[:7]}...{api_key[-4:]}"

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
        Send chat request to OpenAI Responses API for GPT 4o Mini.
        On any error, immediately raise exception to trigger next model in multi-provider.
        """
        try:
            # Wait for rate limit slot
            await self.wait_for_slot()

            # Convert messages to single input text
            # Combine all messages into a single prompt
            input_text = ""
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    input_text += f"System: {content}\n\n"
                elif role == "user":
                    input_text += f"User: {content}\n\n"
                elif role == "assistant":
                    input_text += f"Assistant: {content}\n\n"
            
            # Remove trailing newlines
            input_text = input_text.strip()

            # Prepare payload for Responses API
            payload = {
                "model": self.model_name,
                "input": input_text,
                "store": True,
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            # Make request using httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/responses",
                    headers=headers,
                    json=payload,
                )

                response.raise_for_status()
                data = response.json()

                # Extract text from response
                output_text = None
                
                # Try direct output_text field
                if isinstance(data.get("output_text"), str):
                    output_text = data["output_text"]
                # Try output array structure (OpenAI Responses API format)
                elif "output" in data and isinstance(data["output"], list):
                    for item in data["output"]:
                        if isinstance(item, dict):
                            # Look for items with type 'message'
                            if item.get("type") == "message":
                                # Get the content array
                                content_list = item.get("content", [])
                                if isinstance(content_list, list):
                                    for content_item in content_list:
                                        if isinstance(content_item, dict):
                                            # Look for content items with type 'output_text'
                                            if content_item.get("type") == "output_text":
                                                text = content_item.get("text")
                                                if isinstance(text, str):
                                                    output_text = text
                                                    break
                                    if output_text:
                                        break
                            # Fallback: try direct content field (if it's a string)
                            elif "content" in item:
                                content = item["content"]
                                if isinstance(content, str):
                                    output_text = content
                                    break
                            # Fallback: try direct text field
                            elif "text" in item:
                                output_text = item["text"]
                                break
                # Try choices (ChatGPT-style)
                elif "choices" in data and isinstance(data["choices"], list):
                    for choice in data["choices"]:
                        if isinstance(choice, dict):
                            msg = choice.get("message", {})
                            if isinstance(msg, dict) and "content" in msg:
                                output_text = msg["content"]
                                break

                if output_text:
                    return output_text.strip()
                else:
                    logger.warning(f"OpenAI returned response but couldn't extract text. Full response: {data}")
                    import json
                    response_str = json.dumps(data)
                    return response_str[:500]  # Fallback: return first 500 chars of JSON

        except Exception as exc:
            # On any error, immediately raise to trigger next model in multi-provider
            error_str = str(exc)
            status_code = getattr(exc, 'status_code', None)
            if hasattr(exc, 'response') and hasattr(exc.response, 'status_code'):
                status_code = exc.response.status_code
            
            # Log the error with API key info for debugging
            masked_key = self._mask_api_key(self.api_key)
            if status_code == 429 or "429" in error_str or "rate limit" in error_str.lower() or "quota" in error_str.lower():
                logger.warning(
                    f"GPT 4o Mini rate limit error (429): {exc}\n"
                    f"[OPENAI_API_KEY] Using API key: {masked_key} (length: {len(self.api_key)})\n"
                    f"[DEBUG] Check OpenAI dashboard for this key: https://platform.openai.com/api-keys"
                )
            elif status_code == 503 or "503" in error_str or "unavailable" in error_str.lower():
                logger.warning(f"GPT 4o Mini server unavailable (503): {exc}")
            elif status_code == 401 or "401" in error_str or "unauthorized" in error_str.lower():
                logger.warning(f"GPT 4o Mini authentication error (401): {exc}")
            else:
                logger.error(f"GPT 4o Mini API error: {exc}")
            
            # Raise immediately to trigger next model
            raise

    def get_provider_name(self) -> str:
        return "GPT 4o Mini"

