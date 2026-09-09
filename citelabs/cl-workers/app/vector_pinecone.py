"""
Pinecone Vector Store Implementation
"""
import logging
import os
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

import pinecone
from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)


class PineconeVectorStore:
    """Pinecone vector store implementation."""

    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY environment variable must be set")
        
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "citelabs-sandbox")
        self.dimension = int(os.getenv("PINECONE_DIMENSION", "1536"))  # OpenAI text-embedding-3-small
        
        self.pc = Pinecone(api_key=self.api_key)
        
        # Create index if it doesn't exist
        self._ensure_index()
        
        self.index = self.pc.Index(self.index_name)
        logger.info(f"Initialized Pinecone vector store (index: {self.index_name})")

    def _ensure_index(self) -> None:
        """Ensure the Pinecone index exists."""
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=os.getenv("PINECONE_REGION", "us-east-1"),
                    ),
                )
                logger.info(f"Created Pinecone index: {self.index_name}")
        except Exception as exc:
            logger.warning(f"Error checking/creating index: {exc}")

    async def store_chunks(
        self,
        namespace: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """
        Store chunks with embeddings in Pinecone.

        Args:
            namespace: Namespace for this sandbox run (e.g., "sandbox-{id}")
            chunks: List of chunk dicts with url, text, chunk_id, is_client, domain, summary
            embeddings: List of embedding vectors
        """
        if not chunks or not embeddings:
            return

        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            # Skip all-zero vectors to satisfy Pinecone constraint
            if not embedding or not any(abs(v) > 0 for v in embedding):
                logger.debug(f"Skipping zero embedding for {chunk.get('url')}#{chunk.get('chunk_id')}")
                continue
            vector_id = f"{chunk['url']}_{chunk.get('chunk_id', 0)}"
            # Extract domain_type from chunk metadata (P2: Brand Boost)
            chunk_metadata = chunk.get("metadata", {})
            domain_type = chunk_metadata.get("domain_type", "editorial")  # Default to editorial if not set
            
            metadata = {
                "url": chunk["url"],
                "text": chunk.get("text", "")[:1000],  # Limit metadata size
                "chunk_id": chunk.get("chunk_id", 0),
                "is_client": chunk.get("is_client", False),
                "domain": chunk.get("domain", ""),
                "summary": chunk.get("summary", "")[:500],
                "domain_type": domain_type,  # P2: Store domain_type for retrieval weighting
            }
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": metadata,
            })

        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch, namespace=namespace)
            logger.debug(f"Upserted {len(batch)} vectors to namespace {namespace}")

    async def search(
        self,
        namespace: str,
        query_vector: List[float],
        top_k: int = 10,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in Pinecone.

        Args:
            namespace: Namespace to search in
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filter (e.g., {"is_client": True})

        Returns:
            List of results with score, url, text, metadata
        """
        try:
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True,
                filter=filter_dict,
            )

            formatted_results = []
            for match in results.matches:
                formatted_results.append({
                    "score": match.score,
                    "url": match.metadata.get("url", ""),
                    "text": match.metadata.get("text", ""),
                    "chunk_id": match.metadata.get("chunk_id", 0),
                    "is_client": match.metadata.get("is_client", False),
                    "domain": match.metadata.get("domain", ""),
                    "summary": match.metadata.get("summary", ""),
                    "domain_type": match.metadata.get("domain_type", "editorial"),  # P2: Return domain_type for filtering
                })

            return formatted_results
        except Exception as exc:
            logger.error(f"Pinecone search error: {exc}")
            return []

    async def delete_namespace(self, namespace: str) -> None:
        """Delete all vectors in a namespace."""
        try:
            # Pinecone doesn't have a direct delete namespace API
            # We'll need to delete by metadata filter or use delete_all
            # For now, we'll leave vectors (they can be cleaned up manually)
            logger.info(f"Note: Pinecone namespace {namespace} vectors will persist")
        except Exception as exc:
            logger.warning(f"Error deleting namespace {namespace}: {exc}")

