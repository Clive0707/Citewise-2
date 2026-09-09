"""
Fixed-size chunker implementation.
"""
from typing import Any, Dict, List
from urllib.parse import urlparse

from . import Document
from .base import Chunker


class FixedSizeChunker(Chunker):
    """Fixed-size chunker that splits text at fixed character boundaries."""
    
    def __init__(self, chunk_size: int = 1500, overlap: int = 200):
        """
        Initialize fixed-size chunker.
        
        Args:
            chunk_size: Target chunk size in characters (default: 1500)
            overlap: Overlap between chunks in characters (default: 200)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_documents(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Chunk documents using fixed-size splitting.
        
        Args:
            documents: List of Document objects to chunk
            
        Returns:
            List of chunk dictionaries matching the required schema
        """
        all_chunks = []
        
        for doc in documents:
            if not doc.text or not doc.text.strip():
                continue
            
            # Extract metadata
            metadata = doc.metadata or {}
            url = metadata.get("url", doc.source)
            is_client = metadata.get("is_client", False)
            domain = metadata.get("domain")
            if not domain:
                domain = urlparse(url).netloc
            
            source_type = metadata.get("source_type")
            if not source_type:
                source_type = "client" if is_client else "competitor"
            
            # Chunk the text
            chunks = self._chunk_text(
                text=doc.text,
                url=url,
                is_client=is_client,
                domain=domain,
                source_type=source_type
            )
            
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def _chunk_text(
        self,
        text: str,
        url: str,
        is_client: bool,
        domain: str,
        source_type: str
    ) -> List[Dict[str, Any]]:
        """
        Chunk text into fixed-size chunks.
        
        Args:
            text: Text to chunk
            url: Source URL
            is_client: Whether this is the client page
            domain: Domain name
            source_type: Source type ("client" or "competitor")
            
        Returns:
            List of chunk dicts
        """
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunks.append({
                    "url": url,
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "summary": chunk_text[:200],  # Simple summary
                    "is_client": is_client,
                    "domain": domain,
                    "source_type": source_type,
                })
                chunk_id += 1
            
            start = end - self.overlap
            if start >= len(text):
                break
        
        return chunks

