"""
Chunking module for document processing.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

__all__ = ["Document"]


@dataclass
class Document:
    """Simple document representation for chunking."""
    text: str
    source: str  # URL or identifier
    metadata: Optional[Dict[str, Any]] = None

