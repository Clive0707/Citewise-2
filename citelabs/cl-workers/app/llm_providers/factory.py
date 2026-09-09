"""
LLM Provider Factory
"""
import os
import logging
from typing import Optional
from .base import BaseLLMProvider
from .gemini import Gemini25FlashProvider, Gemini15ProProvider
from .openai import GPT4oMiniProvider, GPT5NanoProvider
from .mistral import MistralProvider
from ..constants import *

# Global provider cache
_provider_cache: dict[str, BaseLLMProvider] = {}
logger = logging.getLogger(__name__)


def get_llm_provider(model_name: Optional[str] = None) -> BaseLLMProvider:
    """
    Get an LLM provider instance.
    
    Args:
        model: Provider name (model constant from constants.py)
              If None, uses LLM_PROVIDER env var (defaults to "gemini")
    
    Returns:
        BaseLLMProvider instance
    """
    logger.info(f"Getting LLM provider for model: {model_name}")
    if model_name is None:
        model_name = os.getenv("LLM_PROVIDER", MODEL_GEMINI_2_5_FLASH).lower()
    else:
        model_name = model_name.lower()

    # Check cache
    if model_name in _provider_cache:
        return _provider_cache[model_name]

    # Create new provider
    if model_name == MODEL_GEMINI_2_5_FLASH:
        if Gemini25FlashProvider is None:
            logger.error("Gemini 2.5 Flash provider requested but 'gemini' package is not installed. Install it with: pip install gemini-ai")
            raise ImportError("Gemini 2.5 Flash provider requires 'gemini-ai' package. Install it with: pip install gemini-ai")
        provider = Gemini25FlashProvider()
    elif model_name == MODEL_GEMINI_1_5_PRO:
        if Gemini15ProProvider is None:
            logger.error("Gemini 1.5 Pro provider requested but 'gemini' package is not installed. Install it with: pip install gemini-ai")
            raise ImportError("Gemini 1.5 Pro provider requires 'gemini-ai' package. Install it with: pip install gemini-ai")
        provider = Gemini15ProProvider()
    elif model_name == MODEL_GPT_5_NANO:
        if GPT5NanoProvider is None:
            logger.error("GPT 5 Nano provider requested but 'openai' package is not installed. Install it with: pip install openai")
            raise ImportError("GPT 5 Nano provider requires 'openai' package. Install it with: pip install openai")
        provider = GPT5NanoProvider()
    elif model_name == MODEL_GPT_4_O_MINI:
        if GPT4oMiniProvider is None:
            logger.error("GPT 4o Mini provider requested but 'openai' package is not installed. Install it with: pip install openai")
            raise ImportError("GPT 4o Mini provider requires 'openai' package. Install it with: pip install openai")
        provider = GPT4oMiniProvider()
    elif model_name == MODEL_MISTRAL_MEDIUM_LATEST:
        if MistralProvider is None:
            logger.error("Mistral provider requested but 'mistralai' package is not installed. Install it with: pip install mistralai")
            raise ImportError("Mistral provider requires 'mistralai' package. Install it with: pip install mistralai")
        provider = MistralProvider()
    else:
        logger.warning(f"Unknown provider '{model_name}', defaulting to Gemini")
        provider = Gemini25FlashProvider()

    _provider_cache[model_name] = provider
    return provider
