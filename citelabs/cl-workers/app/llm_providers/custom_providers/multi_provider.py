"""
Multi-Provider LLM Wrapper
Attempts models in order with proper error handling, retries, and timeouts.
"""
import asyncio
import logging
from typing import List, Dict, Optional

from ..factory import get_llm_provider
from ..base import BaseLLMProvider
from ...constants import (
    MODEL_GEMINI_2_5_FLASH,
    MODEL_MISTRAL_MEDIUM_LATEST,
    MODEL_GPT_4_O_MINI,
    MODEL_GPT_5_NANO,
)

logger = logging.getLogger(__name__)


class MultiProviderLLM:
    """
    Multi-provider LLM wrapper that attempts models in order:
    1. MODEL_GEMINI_2_5_FLASH
    2. MODEL_MISTRAL_MEDIUM_LATEST
    3. MODEL_GPT_4_O_MINI
    4. MODEL_GPT_5_NANO
    """
    
    def __init__(
        self,
        per_model_retries: int = 1,
        per_call_timeout: float = 120.0,
        model_attempt_delay: float = 5.0,
    ):
        """
        Initialize multi-provider wrapper.
        
        Args:
            per_model_retries: Number of retries per model before moving to next (default: 1)
            per_call_timeout: Timeout in seconds for each API call (default: 15.0)
            model_attempt_delay: Delay in seconds before attempting each model (default: 5.0)
        """
        self.per_model_retries = per_model_retries
        self.per_call_timeout = per_call_timeout
        self.model_attempt_delay = model_attempt_delay
        
        # Model order as specified
        self.model_order = [
            MODEL_GEMINI_2_5_FLASH,
            MODEL_MISTRAL_MEDIUM_LATEST,
            MODEL_GPT_4_O_MINI,
            MODEL_GPT_5_NANO,
        ]
        
        # Provider cache
        self._provider_cache: Dict[str, BaseLLMProvider] = {}
        self._last_used_model: Optional[str] = None
    
    def _get_provider_for_model(self, model: str) -> Optional[BaseLLMProvider]:
        """
        Get the appropriate provider for a given model.
        
        Args:
            model: Model name
            
        Returns:
            BaseLLMProvider instance or None if provider not available
        """
        # Map model to provider name
        provider_name = None
        if model in [MODEL_GEMINI_2_5_FLASH, MODEL_MISTRAL_MEDIUM_LATEST, MODEL_GPT_4_O_MINI, MODEL_GPT_5_NANO]:
            provider_name = model
        else:
            logger.warning(f"Unknown model {model}, cannot determine provider")
            return None
        
        # Check cache
        if provider_name in self._provider_cache:
            return self._provider_cache[provider_name]
        
        # Create provider
        try:
            provider = get_llm_provider(provider_name)
            self._provider_cache[provider_name] = provider
            return provider
        except Exception as exc:
            logger.warning(f"Failed to initialize provider {provider_name} for model {model}: {exc}")
            return None
    
    def _is_transient_error(self, exc: Exception) -> bool:
        """
        Check if an error is transient (should try next model).
        
        Args:
            exc: Exception to check
            
        Returns:
            True if error is transient, False if fatal
        """
        error_str = str(exc).lower()
        status_code = getattr(exc, 'status_code', None)
        
        # Network errors
        if "timeout" in error_str or "connection" in error_str or "network" in error_str:
            return True
        
        # Rate limit errors
        if status_code == 429 or "429" in error_str or "rate limit" in error_str or "quota" in error_str:
            return True
        
        # Server errors (5xx)
        if status_code and 500 <= status_code < 600:
            return True
        if "503" in error_str or "502" in error_str or "500" in error_str or "unavailable" in error_str:
            return True
        
        # All other errors are considered fatal but non-crashing
        # (invalid API key, bad request, etc.) - we'll try next model
        return False
    
    def _is_fatal_error(self, exc: Exception) -> bool:
        """
        Check if an error is fatal (invalid API key, bad request, etc.).
        These should log and try next model, not crash.
        
        Args:
            exc: Exception to check
            
        Returns:
            True if error is fatal (but non-crashing)
        """
        error_str = str(exc).lower()
        status_code = getattr(exc, 'status_code', None)
        
        # Authentication errors
        if status_code == 401 or "401" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
            return True
        
        # Bad request errors
        if status_code == 400 or "400" in error_str or "bad request" in error_str:
            return True
        
        # Not found errors
        if status_code == 404 or "404" in error_str or "not found" in error_str:
            return True
        
        return False
    
    async def chat(
        self,
        messages: List[Dict[str, str]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Attempt chat completion with models in order.
        
        Args:
            messages: Chat messages
            max_tokens: Max tokens
            temperature: Temperature
            
        Returns:
            Generated text response
            
        Raises:
            Exception if all models fail
        """
        if messages is None:
            messages = []
        
        last_error = None
        
        # Try each model in order
        for model_name in self.model_order:
            # Wait before attempting each model (including the first one)
            logger.info(f"⏳ Waiting {self.model_attempt_delay} seconds before attempting {model_name}...")
            await asyncio.sleep(self.model_attempt_delay)
            
            provider = self._get_provider_for_model(model_name)
            
            if provider is None:
                logger.warning(f"Skipping model {model_name} - provider not available")
                continue
            
            # Try with retries
            for attempt in range(self.per_model_retries + 1):
                try:
                    logger.debug(
                        f"Attempting {model_name} (attempt {attempt + 1}/{self.per_model_retries + 1})"
                    )
                    
                    # Make call with timeout
                    response = await asyncio.wait_for(
                        provider.chat(
                            messages=messages,
                            max_tokens=max_tokens,
                            temperature=temperature,
                        ),
                        timeout=self.per_call_timeout,
                    )
                    
                    # Success - return immediately
                    self._last_used_model = model_name
                    logger.info(f"✅ Successfully used {model_name}")
                    return response
                    
                except asyncio.TimeoutError:
                    error_msg = f"Timeout after {self.per_call_timeout}s"
                    logger.warning(f"⏱️ {model_name} {error_msg}")
                    last_error = Exception(error_msg)
                    
                    # Timeout is transient - try next model if this was last attempt
                    if attempt < self.per_model_retries:
                        continue
                    else:
                        break  # Move to next model
                        
                except Exception as exc:
                    last_error = exc
                    error_str = str(exc)
                    
                    # Check error type
                    if self._is_transient_error(exc):
                        logger.warning(
                            f"⚠️ {model_name} transient error: {exc}. "
                            f"{'Retrying...' if attempt < self.per_model_retries else 'Moving to next model...'}"
                        )
                        if attempt < self.per_model_retries:
                            # Wait a bit before retry
                            await asyncio.sleep(0.5 * (attempt + 1))
                            continue
                        else:
                            break  # Move to next model
                    elif self._is_fatal_error(exc):
                        logger.warning(
                            f"⚠️ {model_name} fatal error (non-crashing): {exc}. Moving to next model..."
                        )
                        break  # Move to next model
                    else:
                        # Unknown error - log and move to next model
                        logger.warning(
                            f"⚠️ {model_name} error: {exc}. Moving to next model..."
                        )
                        break  # Move to next model
        
        # All models failed
        error_msg = f"All models failed. Last error: {last_error}"
        logger.error(f"❌ {error_msg}")
        raise Exception(error_msg)
    
    def get_provider_name(self) -> str:
        """Return combined provider name."""
        return f"MultiProvider (last used: {self._last_used_model or 'none'})"
    
    def get_last_used_model(self) -> Optional[str]:
        """Get the last successfully used model."""
        return self._last_used_model


# Global multi-provider instance
_multi_provider: Optional[MultiProviderLLM] = None


def get_multi_provider_llm(
    per_model_retries: int = 1,
    per_call_timeout: float = 15.0,
    model_attempt_delay: float = 5.0,
) -> MultiProviderLLM:
    """
    Get the global multi-provider LLM instance.
    
    Args:
        per_model_retries: Number of retries per model (default: 1)
        per_call_timeout: Timeout per call in seconds (default: 15.0)
        model_attempt_delay: Delay in seconds before attempting each model (default: 5.0)
    
    Returns:
        MultiProviderLLM instance
    """
    global _multi_provider
    if _multi_provider is None:
        _multi_provider = MultiProviderLLM(
            per_model_retries=per_model_retries,
            per_call_timeout=per_call_timeout,
            model_attempt_delay=model_attempt_delay,
        )
    return _multi_provider

