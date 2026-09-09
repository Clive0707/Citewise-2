"""
Supabase Vector Store Implementation

Cloud-based, persistent vector storage using Supabase (PostgreSQL + pgvector).
Vectors are persisted across queries for better performance and caching.
"""
import logging
import os
from typing import Any, Dict, List

from supabase import create_client, Client

from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class SupabaseVectorStore(VectorStore):
    """Supabase-based persistent vector store using pgvector."""

    def __init__(self):
        self.client: Client = None
        self.table_name = "citelabs_pages"
        self._init_client()

    def _init_client(self):
        """Initialize Supabase client."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY environment variables must be set"
            )

        self.client = create_client(supabase_url, supabase_key)
        logger.info(f"Supabase client initialized: {supabase_url}")

    async def store_vectors(
        self,
        entries: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """
        Store vectors in Supabase database.

        Args:
            entries: List of entry dictionaries
            embeddings: List of embedding vectors
        """
        if not entries or not embeddings:
            logger.warning("No entries or embeddings provided to Supabase store")
            return

        if len(entries) != len(embeddings):
            raise ValueError(
                f"Entries ({len(entries)}) and embeddings ({len(embeddings)}) length mismatch"
            )

        # Prepare records for insertion
        records = []
        for entry, embedding in zip(entries, embeddings):
            records.append(
                {
                    "url": entry["url"],
                    "content": entry["content"][:2000],  # Limit content size
                    "ai_summary": entry.get("ai_summary", ""),
                    "page_type": entry.get("page_type", "Unknown"),
                    "is_client": entry["is_client"],
                    "embedding": embedding,
                }
            )

        # Insert into Supabase (upsert to avoid duplicates based on URL)
        try:
            # Delete existing entries with same URLs to refresh data
            urls = [entry["url"] for entry in entries]
            self.client.table(self.table_name).delete().in_("url", urls).execute()

            # Insert new entries
            response = self.client.table(self.table_name).insert(records).execute()

            logger.info(
                f"Stored {len(records)} vectors in Supabase (table={self.table_name})"
            )
        except Exception as e:
            logger.error(f"Failed to store vectors in Supabase: {e}")
            raise

    async def search(
        self,
        query_vector: List[float],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search Supabase for similar vectors using pgvector.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results

        Returns:
            List of results with scores and metadata
        """
        try:
            # Call the RPC function for vector similarity search
            response = (
                self.client.rpc(
                    "match_pages",
                    {
                        "query_embedding": query_vector,
                        "match_threshold": 0.0,  # No threshold, return all matches
                        "match_count": limit,
                    },
                )
                .execute()
            )

            results = []
            for row in response.data:
                results.append(
                    {
                        "url": row["url"],
                        "score": float(row["similarity"]),
                        "ai_summary": row["ai_summary"],
                        "page_type": row["page_type"],
                        "is_client": row["is_client"],
                    }
                )

            logger.info(f"Supabase search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Failed to search Supabase: {e}")
            raise

    async def clear(self) -> None:
        """
        Clear all entries from Supabase table.
        WARNING: This deletes all data!
        """
        try:
            # Delete all rows (use with caution in production)
            self.client.table(self.table_name).delete().neq("id", 0).execute()
            logger.info(f"Cleared all entries from Supabase table {self.table_name}")
        except Exception as e:
            logger.error(f"Failed to clear Supabase table: {e}")
            raise

