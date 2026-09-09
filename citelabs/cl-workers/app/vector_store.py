"""
Vector Store Abstraction Layer

This module provides a unified interface for different vector database backends.
Supports: FAISS (local, in-memory) and Supabase (cloud, persistent)

Switch between providers using VECTOR_DB_PROVIDER environment variable.
"""
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Abstract base class for vector storage implementations."""

    @abstractmethod
    async def store_vectors(
        self,
        entries: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """
        Store vectors and their associated metadata.

        Args:
            entries: List of entry dictionaries containing url, content, metadata
            embeddings: List of embedding vectors (same length as entries)
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            query_vector: The query embedding vector
            limit: Maximum number of results to return

        Returns:
            List of results with 'score' and metadata fields
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear/reset the vector store."""
        pass


def get_vector_store() -> VectorStore:
    """
    Factory function to get the configured vector store.

    Returns the appropriate VectorStore implementation based on
    VECTOR_DB_PROVIDER environment variable.

    Returns:
        VectorStore: Configured vector store instance

    Environment Variables:
        VECTOR_DB_PROVIDER: "supabase" or "faiss" (default: "faiss")
    """
    provider = os.getenv("VECTOR_DB_PROVIDER", "faiss").lower()

    if provider == "supabase":
        logger.info("Using Supabase vector store")
        from .vector_supabase import SupabaseVectorStore

        return SupabaseVectorStore()
    elif provider == "faiss":
        logger.info("Using FAISS vector store (in-memory)")
        from .vector_faiss import FaissVectorStore

        return FaissVectorStore()
    else:
        logger.warning(
            f"Unknown VECTOR_DB_PROVIDER '{provider}', defaulting to FAISS"
        )
        from .vector_faiss import FaissVectorStore

        return FaissVectorStore()




