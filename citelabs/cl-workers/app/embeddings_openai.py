"""
OpenAI Embeddings Module
Uses text-embedding-3-small model
"""
import os
import logging
from typing import List, Optional

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None  # Will raise error if used without package

logger = logging.getLogger(__name__)

_model_name = "text-embedding-3-small"
_dimension = 1536
_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    """Get or create OpenAI client."""
    global _client
    if AsyncOpenAI is None:
        raise ImportError("'openai' package is required for OpenAI embeddings. Install it with: pip install openai")
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be set")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


async def embed_documents(documents: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple documents using OpenAI.

    Args:
        documents: List of text documents

    Returns:
        List of embedding vectors (each is a list of floats)
    """
    if not documents:
        return []

    client = _get_client()
    
    # Filter out empty documents
    non_empty = [doc.strip() if doc else "" for doc in documents]
    non_empty = [doc for doc in non_empty if doc]
    
    if not non_empty:
        return []

    try:
        response = await client.embeddings.create(
            model=_model_name,
            input=non_empty,
        )

        embeddings = [item.embedding for item in response.data]
        
        # Pad with empty embeddings for empty documents
        result = []
        doc_idx = 0
        for doc in documents:
            if doc and doc.strip():
                result.append(embeddings[doc_idx])
                doc_idx += 1
            else:
                result.append([0.0] * _dimension)
        
        return result
    except Exception as exc:
        logger.error(f"OpenAI embeddings error: {exc}")
        raise


async def embed_query(query: str) -> List[float]:
    """
    Generate embedding for a single query.

    Args:
        query: Query text

    Returns:
        Embedding vector (list of floats)
    """
    if not query or not query.strip():
        return [0.0] * _dimension

    results = await embed_documents([query])
    return results[0] if results else [0.0] * _dimension

