"""
Base chunker interface.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from . import Document


class Chunker(ABC):
    """Abstract base class for chunkers."""
    
    @abstractmethod
    def chunk_documents(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Chunk documents into smaller pieces.
        
        Args:
            documents: List of Document objects to chunk
            
        Returns:
            List of chunk dictionaries with the following keys:
            - url: str
            - chunk_id: int
            - text: str
            - summary: str (first 200 chars)
            - is_client: bool
            - domain: str
            - source_type: str ("client" or "competitor")
        """
        pass

