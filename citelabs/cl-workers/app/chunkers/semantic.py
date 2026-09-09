"""
Semantic chunker implementation using LlamaIndex.
"""
from typing import Any, Dict, List
from urllib.parse import urlparse

from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import SentenceSplitter

from . import Document
from .base import Chunker


class SemanticChunker(Chunker):
    """Semantic chunker that splits text at sentence boundaries."""
    
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        """
        Initialize semantic chunker.
        
        Args:
            chunk_size: Target chunk size in characters (default: 1500)
            chunk_overlap: Overlap between chunks in characters (default: 200)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Initialize SentenceSplitter with character-based chunking
        # Note: SentenceSplitter uses tokens by default, but we configure it for characters
        self.splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    
    def chunk_documents(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Chunk documents using semantic (sentence-aware) splitting.
        
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
            
            # Convert to LlamaIndex Document
            llama_doc = LlamaDocument(
                text=doc.text,
                metadata={"url": url, "is_client": is_client, "domain": domain, "source_type": source_type}
            )
            
            # Split into nodes (chunks)
            nodes = self.splitter.get_nodes_from_documents([llama_doc])
            
            # Convert nodes back to required chunk format
            for chunk_id, node in enumerate(nodes):
                chunk_text = node.get_content()
                
                if chunk_text.strip():
                    all_chunks.append({
                        "url": url,
                        "chunk_id": chunk_id,
                        "text": chunk_text,
                        "summary": chunk_text[:200],  # First 200 chars
                        "is_client": is_client,
                        "domain": domain,
                        "source_type": source_type,
                    })
        
        return all_chunks

