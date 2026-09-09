"""
Chunker factory for creating chunker instances based on configuration.
"""
import os

from ..constants import CHUNKING_TYPE_SEMENTIC
from .fixed_size import FixedSizeChunker
from .semantic import SemanticChunker


def get_chunker():
    """
    Get the appropriate chunker instance based on CHUNKING_TYPE environment variable.
    
    Returns:
        Chunker instance (FixedSizeChunker or SemanticChunker)
    """
    chunking_type = os.getenv("CHUNKING_TYPE", "").upper()
    
    if chunking_type == CHUNKING_TYPE_SEMENTIC:
        return SemanticChunker()
    else:
        # Default to fixed-size chunking
        return FixedSizeChunker()

