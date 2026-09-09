"""
FAISS Vector Store Implementation

In-memory, local vector storage using Facebook's FAISS library.
Data is not persisted - rebuilt fresh for each query.
"""
import logging
from typing import Any, Dict, List

import faiss
import numpy as np

from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class FaissVectorStore(VectorStore):
    """FAISS-based in-memory vector store."""

    def __init__(self):
        self.index = None
        self.entries = []

    async def store_vectors(
        self,
        entries: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """
        Store vectors in FAISS index (in-memory).

        Args:
            entries: List of entry dictionaries
            embeddings: List of embedding vectors
        """
        if not entries or not embeddings:
            logger.warning("No entries or embeddings provided to FAISS store")
            return

        if len(entries) != len(embeddings):
            raise ValueError(
                f"Entries ({len(entries)}) and embeddings ({len(embeddings)}) length mismatch"
            )

        # Store entries for later retrieval
        self.entries = entries

        # Convert embeddings to numpy array
        embeddings_np = np.asarray(embeddings, dtype="float32")

        if embeddings_np.size == 0:
            logger.warning("Empty embeddings array")
            return

        # Create FAISS index
        dimension = embeddings_np.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product (cosine similarity)
        self.index.add(embeddings_np)

        logger.info(f"Stored {len(entries)} vectors in FAISS (dimension={dimension})")

    async def search(
        self,
        query_vector: List[float],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search FAISS index for similar vectors.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results

        Returns:
            List of results with scores and metadata
        """
        if self.index is None or not self.entries:
            logger.warning("FAISS index not initialized or no entries")
            return []

        # Convert query to numpy array
        query_np = np.asarray([query_vector], dtype="float32")

        # Search
        limit = min(limit, len(self.entries))
        scores, indices = self.index.search(query_np, limit)

        # Build results
        results = []
        for idx, score in zip(indices[0], scores[0]):
            entry = self.entries[idx]
            results.append(
                {
                    "url": entry["url"],
                    "score": float(score),
                    "ai_summary": entry["ai_summary"],
                    "page_type": entry["page_type"],
                    "is_client": entry["is_client"],
                }
            )

        logger.info(f"FAISS search returned {len(results)} results")
        return results

    async def clear(self) -> None:
        """Clear FAISS index and entries."""
        self.index = None
        self.entries = []
        logger.info("FAISS store cleared")




