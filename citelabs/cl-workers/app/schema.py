from typing import Any, Dict

from . import llm


async def generate_schema(page_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate JSON-LD schema and AI summary from crawled page data.
    """
    # Build a summary of the page content
    content_for_summary = f"""
Page Title: {page_record.get('title', 'N/A')}
Meta Description: {page_record.get('metaDescription', 'N/A')}
Page Type: {page_record.get('pageType', 'N/A')}
Keywords: {', '.join(page_record.get('keywords', [])[:10])}
Page Purpose: {page_record.get('pagePurposeSummary', 'N/A')}
""".strip()

    # Generate AI summary using the LLM
    ai_summary = await llm.generate_llm_summary(content_for_summary, short=True)
    
    # If AI summary is empty (e.g., Gemini blocked), use page purpose or description as fallback
    if not ai_summary:
        ai_summary = page_record.get('pagePurposeSummary') or page_record.get('metaDescription') or "No summary available"

    return {
        "jsonld": {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": page_record.get("title"),
            "description": page_record.get("metaDescription"),
            "url": page_record.get("url"),
            "keywords": page_record.get("keywords", []),
        },
        "ai_summary": ai_summary,
    }

