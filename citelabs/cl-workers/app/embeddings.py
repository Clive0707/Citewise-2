import os
from typing import Iterable, List, Optional, Sequence

import numpy as np
from sentence_transformers import SentenceTransformer

_MODEL_NAME = os.getenv("EMBEDDINGS_MODEL", "BAAI/bge-small-en-v1.5")
_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_documents(documents: Iterable[str]) -> List[List[float]]:
    texts: List[str] = [doc.strip() if doc else "" for doc in documents]
    if not texts:
        return []

    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    if isinstance(embeddings, list):
        return embeddings
    return embeddings.tolist()


def embed_query(query: str) -> List[float]:
    [vector] = embed_documents([query])
    return vector


def as_float32_matrix(vectors: Sequence[Sequence[float]]) -> np.ndarray:
    if not vectors:
        return np.empty((0, 0), dtype="float32")
    return np.asarray(vectors, dtype="float32")

