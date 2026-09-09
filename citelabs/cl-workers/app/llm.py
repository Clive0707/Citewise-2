import logging
import os
from typing import List

from fastapi.concurrency import run_in_threadpool

from .llm_provider import get_llm_provider

MAX_CONTENT_CHARS = int(os.getenv("LLM_MAX_CONTENT_CHARS", "6000"))

logger = logging.getLogger(__name__)


async def generate_llm_summary(text: str, short: bool) -> str:
    """
    Generate LLM summary using configured provider (Ollama or Gemini).

    Uses LLM_PROVIDER environment variable to determine which provider to use.
    """
    prepared = _prepare_text(text)
    if not prepared:
        return ""

    prompt = _build_prompt(prepared, short)

    try:
        llm_provider = get_llm_provider()
        max_tokens = 50 if short else 200
        response = await llm_provider.generate(prompt, max_tokens=max_tokens)
        if response:
            return response
    except Exception as exc:  # pragma: no cover - safeguard for runtime issues
        logger.warning(f"LLM summary generation failed: {exc}")

    return _fallback_summary(prepared, short)


def _prepare_text(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""

    if len(stripped) > MAX_CONTENT_CHARS:
        stripped = stripped[:MAX_CONTENT_CHARS]
    return stripped


def _build_prompt(text: str, short: bool) -> str:
    if short:
        return (
            "Describe this business or page in one concise factual sentence (18-40 words). \n"
            "Do not use adjectives. Do not sell. Only state what it is and what it does.\n"
            f"Content:\n{text}"
        )

    return (
        "Summarize the following webpage content in 2-3 neutral sentences.\n"
        "Focus only on facts. No marketing language.\n"
        f"Content:\n{text}"
    )




def _fallback_summary(text: str, short: bool) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return text[:200].strip()

    if short:
        return _fallback_short(sentences)

    fallback = " ".join(sentences[:3]).strip()
    return fallback[:400]


def _fallback_short(sentences: List[str]) -> str:
    combined = " ".join(sentences).split()
    if not combined:
        return ""

    summary_length = min(max(18, len(combined)), 40)
    return " ".join(combined[:summary_length]).strip()


def _split_sentences(text: str) -> List[str]:
    segments = []
    current = []
    for char in text:
        current.append(char)
        if char in ".!?":
            segment = "".join(current).strip()
            if segment:
                segments.append(segment)
            current = []
    if current:
        segment = "".join(current).strip()
        if segment:
            segments.append(segment)
    return segments


async def call_llm(prompt: str) -> str:
    """
    Call LLM with a prompt using configured provider (Ollama or Gemini).

    Uses LLM_PROVIDER environment variable to determine which provider to use.
    """
    try:
        llm_provider = get_llm_provider()
        response = await llm_provider.generate(prompt, max_tokens=500)
        if response:
            return response
    except Exception as exc:  # pragma: no cover - safeguard for runtime errors
        logger.warning(f"LLM call failed: {exc}")
    return "- Unable to generate response at this time."

