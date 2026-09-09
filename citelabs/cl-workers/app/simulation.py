import asyncio
import logging
import os
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests
from fastapi.concurrency import run_in_threadpool

from . import crawl
from .embeddings import embed_documents, embed_query
from .llm import call_llm
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SERP_API_ENDPOINT = os.getenv("SERP_API_ENDPOINT", "https://serpapi.com/search")
MAX_COMPETITORS = 5
PLACEHOLDER_COMPETITORS = [
    "https://www.wikipedia.org",
    "https://www.britannica.com",
    "https://www.nytimes.com",
    "https://www.cnn.com",
    "https://www.reuters.com",
]
_BLOCKED_DOMAINS = {
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "linkedin.com",
    "tiktok.com",
    "youtube.com",
    "pinterest.com",
    "reddit.com",
    "wikipedia.org",
    "cnn.com",
    "nytimes.com",
    "bbc.com",
    "foxnews.com",
    "theguardian.com",
    "reuters.com",
    "bloomberg.com",
}
_BLOCKED_EXTENSIONS = (".pdf", ".doc", ".docx", ".ppt", ".pptx")


async def run_mode_a(url: str, query: str) -> Dict[str, Any]:
    """
    Run simulation mode A: Compare client page against competitors.

    Uses vector store abstraction (FAISS or Supabase) based on VECTOR_DB_PROVIDER.
    """
    # 1. Crawl client page and competitors
    client_page = await crawl.crawl_url(url)
    client_entry = _build_entry(url, client_page, is_client=True)

    competitor_urls = await _fetch_competitor_urls(query, url)
    competitor_pages = await _crawl_competitors(competitor_urls)

    entries = [client_entry] + competitor_pages
    entries = [entry for entry in entries if entry["content"]]

    if not entries:
        return {"rankings": []}

    # 2. Generate embeddings for all entries
    embeddings_matrix = await run_in_threadpool(
        embed_documents,
        [entry["content"] for entry in entries],
    )

    if not embeddings_matrix:
        return {"rankings": []}

    # 3. Get vector store instance (FAISS or Supabase)
    vector_store = get_vector_store()

    # 4. Store vectors in the selected backend
    await vector_store.store_vectors(entries, embeddings_matrix)

    # 5. Generate query embedding and search
    query_vector = await run_in_threadpool(embed_query, query)

    # 6. Search for similar vectors
    ranking = await vector_store.search(query_vector, limit=len(entries))

    if not ranking:
        return {"rankings": []}

    # 7. Attach AI reasoning and fixes
    ranking = await _attach_reasoning(query, ranking)

    return {"rankings": ranking}


async def _fetch_competitor_urls(query: str, origin_url: str) -> List[str]:
    origin_domain = urlparse(origin_url).netloc

    try:
        results = await run_in_threadpool(get_competitor_urls, query, MAX_COMPETITORS)
    except Exception as exc:  # pragma: no cover - safeguard
        logger.warning("Competitor fetch failed, using placeholder competitors: %s", exc)
        results = PLACEHOLDER_COMPETITORS

    filtered: List[str] = []
    for link in results:
        domain = urlparse(link).netloc
        if not domain or domain == origin_domain:
            continue
        if link not in filtered:
            filtered.append(link)
        if len(filtered) >= MAX_COMPETITORS:
            break
    if not filtered:
        filtered = [
            url for url in PLACEHOLDER_COMPETITORS if urlparse(url).netloc != origin_domain
        ][:MAX_COMPETITORS]
    return filtered


async def _crawl_competitors(urls: List[str]) -> List[Dict[str, Any]]:
    tasks = [crawl.crawl_url(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed: List[Dict[str, Any]] = []
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            logger.warning("Failed to crawl competitor %s: %s", url, result)
            continue

        entry = _build_entry(url, result, is_client=False)
        if entry["content"]:
            processed.append(entry)
    return processed


def _build_entry(url: str, page_data: Dict[str, Any], is_client: bool) -> Dict[str, Any]:
    full_content = (page_data or {}).get("full_content") or ""
    ai_summary = (page_data or {}).get("ai_summary") or ""

    content = full_content if full_content.strip() else ai_summary

    return {
        "url": url,
        "ai_summary": ai_summary,
        "page_type": (page_data or {}).get("page_type_guess"),
        "is_client": is_client,
        "content": content.strip(),
    }


def get_competitor_urls(query: str, num_results: int = 5) -> List[str]:
    if not SERPAPI_KEY:
        return PLACEHOLDER_COMPETITORS[:num_results]

    response = requests.get(
        SERP_API_ENDPOINT,
        params={"q": query, "engine": "google", "num": 10, "api_key": SERPAPI_KEY},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()

    organic_results = data.get("organic_results", []) or []
    competitors: List[str] = []

    for item in organic_results:
        link = item.get("link")
        if not link:
            continue

        if not _is_valid_competitor_url(link):
            continue

        if link not in competitors:
            competitors.append(link)

        if len(competitors) >= num_results:
            break

    if not competitors:
        return PLACEHOLDER_COMPETITORS[:num_results]

    return competitors


def _is_valid_competitor_url(link: str) -> bool:
    parsed = urlparse(link)
    if not parsed.scheme.startswith("http"):
        return False

    domain = parsed.netloc.lower()
    if any(blocked in domain for blocked in _BLOCKED_DOMAINS):
        return False

    path_lower = parsed.path.lower()
    if path_lower.endswith(_BLOCKED_EXTENSIONS):
        return False

    return True


async def _attach_reasoning(
    query: str, ranking: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    if not ranking:
        return ranking

    client_summary = next(
        (entry.get("ai_summary") or "" for entry in ranking if entry.get("is_client")), ""
    )
    competitor_summary = next(
        (entry.get("ai_summary") or "" for entry in ranking if not entry.get("is_client")), ""
    )

    enriched: List[Dict[str, Any]] = []
    for entry in ranking:
        comparison_summary = competitor_summary if entry.get("is_client") else entry.get(
            "ai_summary", ""
        )
        reasoning = await explain_ranking(query, client_summary, comparison_summary)
        recommended = (
            await suggest_fixes(query, client_summary) if entry.get("is_client") else ""
        )

        enriched_entry = {
            **entry,
            "reasoning": reasoning,
            "recommended_fixes": recommended,
        }
        enriched.append(enriched_entry)

    return enriched


async def explain_ranking(
    query: str, client_page_summary: str, competitor_page_summary: str
) -> str:
    prompt = (
        "You are an SEO analyst. Provide concise bullet-point reasoning explaining ranking order.\n"
        "Use '-' bullets only. Do not add introductions or conclusions.\n"
        f"Query: {query}\n"
        f"Client Page Summary: {client_page_summary or 'N/A'}\n"
        f"Comparison Page Summary: {competitor_page_summary or 'N/A'}"
    )
    response = await call_llm(prompt)
    return _ensure_bullets(response)


async def suggest_fixes(query: str, client_page_summary: str) -> str:
    prompt = (
        "You are an SEO strategist. Suggest 2-3 factual improvements for the client page.\n"
        "Use '-' bullet points with imperative tone. Avoid marketing language.\n"
        f"Query: {query}\n"
        f"Client Page Summary: {client_page_summary or 'N/A'}"
    )
    response = await call_llm(prompt)
    return _ensure_bullets(response)


def _ensure_bullets(text: str) -> str:
    if not text.strip():
        return "- No insights available."

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    normalized: List[str] = []
    for line in lines:
        if not line.startswith("-"):
            normalized.append(f"- {line}")
        else:
            normalized.append(line)

    return "\n".join(normalized)

