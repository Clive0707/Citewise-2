"""
Gemini LLM Provider Implementation

Cloud-based LLM using Google's Gemini API (New SDK).
Requires GEMINI_API_KEY environment variable.
"""
import logging
import os

from google import genai

from .llm_provider import LLMProvider

logger = logging.getLogger(__name__)


FALLBACK_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
]


class GeminiLLMProvider(LLMProvider):
    """Gemini-based cloud LLM provider using the new google-genai SDK with model pool fallback."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable must be set when using Gemini provider"
            )

        self.fallback_models = FALLBACK_MODELS.copy()
        default_model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
        if default_model in self.fallback_models:
            self.fallback_models.remove(default_model)
        self.fallback_models.insert(0, default_model)

        self.model_index = 0
        self.model_name = self.fallback_models[0]
        self.client = genai.Client(api_key=self.api_key)
        
        from .llm_providers.rate_limiter import get_rate_limiter
        self.rate_limiter = get_rate_limiter()

        logger.warning(f"✅ Initialized Gemini provider (NEW SDK) with model pool: {self.fallback_models}")

    async def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Generate text using Gemini API (New SDK).

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        import asyncio

        try:
            # ==========================================
            # LOG PROMPT FOR DEBUGGING
            # ==========================================
            logger.warning("=" * 80)
            logger.warning("📤 SENDING TO GEMINI (NEW SDK):")
            logger.warning(f"Model: {self.model_name}")
            logger.warning(f"Max Tokens: {max_tokens}")
            logger.warning(f"Prompt Length: {len(prompt)} characters")
            logger.warning("-" * 80)
            logger.warning("TEXT_TO_LLM = '''")
            logger.warning(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            logger.warning("'''")
            logger.warning("=" * 80)
            
            # Generate content using new SDK in threadpool with multi-model pool rotation
            max_retries = len(self.fallback_models) + 1
            for attempt in range(max_retries):
                # Wait for rate limit slot
                await self.rate_limiter.wait_for_slot(self.model_name)
                try:
                    response = await asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model_name,
                        contents=prompt,
                    )
                    if response.text:
                        result = response.text.strip()
                        logger.warning("✅ GEMINI SUCCESS!")
                        logger.warning(f"Response Length: {len(result)} characters")
                        logger.warning(f"Response Preview: {result[:200]}...")
                        logger.warning("=" * 80)
                        return result
                    else:
                        logger.warning("⚠️ Gemini returned empty response")
                        logger.warning("=" * 80)
                        return ""
                except Exception as call_err:
                    err_str = str(call_err)
                    is_rate_or_spike = (
                        "503" in err_str
                        or "429" in err_str
                        or "UNAVAILABLE" in err_str
                        or "demand" in err_str
                        or "RESOURCE_EXHAUSTED" in err_str
                    )
                    if is_rate_or_spike and attempt < max_retries - 1:
                        prev_model = self.model_name
                        self.model_index = (self.model_index + 1) % len(self.fallback_models)
                        self.model_name = self.fallback_models[self.model_index]
                        logger.warning(
                            f"Gemini quota/spike on {prev_model} ({err_str[:60]}). "
                            f"Auto-switching to pool model: {self.model_name} (attempt {attempt + 1}/{max_retries})..."
                        )
                        await asyncio.sleep(1.5)
                        continue
                    raise

        except Exception as exc:
            logger.error(f"❌ Gemini generation failed: {exc}")
            import traceback
            logger.error(traceback.format_exc())
            return ""

    def get_provider_name(self) -> str:
        """Return provider name."""
        return f"Gemini ({self.model_name})"

