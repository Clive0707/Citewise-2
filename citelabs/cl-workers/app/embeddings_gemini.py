# """
# Gemini Embeddings Module (Jan 2025 SDK)
# Uses models/text-embedding-004 via client.embed_content
# """
# import os
# import logging
# import asyncio
# from typing import List

# from google import genai

# logger = logging.getLogger(__name__)

# GEMINI_EMBED_MODEL = "models/text-embedding-004"
# _DIMENSION = 768

# _client: genai.Client | None = None


# def _get_client() -> genai.Client:
#     global _client
#     if _client is None:
#         api_key = os.getenv("GEMINI_API_KEY")
#         if not api_key:
#             raise ValueError("GEMINI_API_KEY must be set for Gemini embeddings")
#         _client = genai.Client(api_key=api_key)
#     return _client


# async def embed_text(text: str) -> List[float]:
#     """Embed a single string using Gemini text-embedding-004."""
#     try:
#         client = _get_client()
#         # res = await asyncio.to_thread(
#         #     client.embed_content,
#         #     model=GEMINI_EMBED_MODEL,
#         #     content=text or "",
#         # )
#         # # Expect dict-like with "embedding"
#         # vec = res.get("embedding") if isinstance(res, dict) else getattr(res, "embedding", None)
#         # if not vec:
#         #     return [0.0] * _DIMENSION
#         # floats = [float(v) for v in vec]
#         res = await asyncio.to_thread(
#             _get_client().models.embed_content,
#             model=GEMINI_EMBED_MODEL,
#             contents=text or ""
#         )
#         vec = getattr(res, "embedding", None)
#         vals = getattr(vec, "values", None)
#         floats = [float(v) for v in (vals or [])]
#         # Normalize dimension
#         if len(floats) != _DIMENSION:
#             if len(floats) > _DIMENSION:
#                 floats = floats[:_DIMENSION]
#             else:
#                 floats = floats + [0.0] * (_DIMENSION - len(floats))
#         return floats
#     except Exception as e:
#         logger.error(f"Gemini embedding error: {e}")
#         raise RuntimeError(f"Gemini embedding error: {e}")


# async def embed_documents(texts: List[str]) -> List[List[float]]:
#     """Manually batch embeddings (Gemini does not support native batch calls)."""
#     logger.info(f"Embedding {len(texts)} chunks with Gemini text-embedding-004")
#     vectors: List[List[float]] = []
#     for t in texts:
#         attempt = 0
#         while True:
#             try:
#                 vec = await embed_text(t)
#                 vectors.append(vec)
#                 break
#             except Exception as e:
#                 if attempt >= 2:
#                     raise
#                 backoff = 2 ** attempt
#                 await asyncio.sleep(backoff)
#                 attempt += 1
#                 continue
#         await asyncio.sleep(0.1)  # small pacing to avoid 429 bursts
#     return vectors



# """
# Gemini Embeddings Module (Jan 2025 SDK)
# Uses models/text-embedding-004 via client.embed_text()
# """

# import os
# import logging
# import asyncio
# from typing import List

# from google import genai

# logger = logging.getLogger(__name__)

# GEMINI_EMBED_MODEL = "models/text-embedding-004"
# _DIMENSION = 768

# _client: genai.Client | None = None


# def _get_client() -> genai.Client:
#     """Create singleton Gemini client."""
#     global _client
#     if _client is None:
#         api_key = os.getenv("GEMINI_API_KEY")
#         if not api_key:
#             raise ValueError("GEMINI_API_KEY must be set for embeddings")
#         _client = genai.Client(api_key=api_key)
#     return _client


# async def embed_text(text: str) -> List[float]:
#     """Embed a single string using Gemini text-embedding-004."""
#     try:
#         client = _get_client()

#         # Correct Jan 2025 API call
#         res = await asyncio.to_thread(
#             client.embed_text,
#             model=GEMINI_EMBED_MODEL,
#             text=text or "",
#         )

#         # Extract embedding vector
#         vec = getattr(res, "embedding", None)
#         if not vec:
#             logger.error("Gemini embedding returned empty embedding object")
#             return [0.0] * _DIMENSION

#         vals = getattr(vec, "values", None)
#         if not vals:
#             logger.error("Gemini embedding returned empty .values list")
#             return [0.0] * _DIMENSION

#         floats = [float(v) for v in vals]

#         # Normalize dimension (just in case)
#         if len(floats) != _DIMENSION:
#             if len(floats) > _DIMENSION:
#                 floats = floats[:_DIMENSION]
#             else:
#                 floats += [0.0] * (_DIMENSION - len(floats))

#         return floats

#     except Exception as e:
#         logger.error(f"Gemini embedding error: {e}")
#         raise RuntimeError(f"Gemini embedding error: {e}")


# async def embed_documents(texts: List[str]) -> List[List[float]]:
#     """Batch embeddings (Gemini has no batch API)."""
#     logger.info(f"Embedding {len(texts)} chunks with Gemini text-embedding-004")

#     vectors = []
#     for t in texts:
#         attempt = 0
#         while True:
#             try:
#                 vec = await embed_text(t)
#                 vectors.append(vec)
#                 break
#             except Exception as e:
#                 if attempt >= 2:
#                     raise
#                 backoff = 2 ** attempt
#                 logger.warning(f"Retrying Gemini embed (attempt {attempt+1}): {e}")
#                 await asyncio.sleep(backoff)
#                 attempt += 1

#         await asyncio.sleep(0.05)  # small delay for safety

#     return vectors

# """
# Gemini Embeddings Module (Jan 2025 SDK)
# Uses models/text-embedding-004 via client.embed_text()
# """

# import os
# import logging
# import asyncio
# from typing import List

# from google import genai

# logger = logging.getLogger(__name__)

# GEMINI_EMBED_MODEL = "models/text-embedding-004"
# _DIMENSION = 768

# _client: genai.Client | None = None


# def _get_client() -> genai.Client:
#     """Create singleton Gemini client."""
#     global _client
#     if _client is None:
#         api_key = os.getenv("GEMINI_API_KEY")
#         if not api_key:
#             raise ValueError("GEMINI_API_KEY must be set for embeddings")
#         _client = genai.Client(api_key=api_key)
#     return _client


# async def embed_text(text: str) -> List[float]:
#     """Embed one string using Gemini text-embedding-004."""
#     try:
#         client = _get_client()

#         # CORRECT Jan 2025 call (matches your working test file)
#         res = await asyncio.to_thread(
#             _get_client().models.embed_content,
#             model=GEMINI_EMBED_MODEL,
#             text=text or "",
#         )

#         # ---- Extract embedding object ----
#         embedding_obj = getattr(res, "embedding", None)
#         if embedding_obj is None:
#             logger.error("❌ Gemini returned no `.embedding` field")
#             return [0.0] * _DIMENSION

#         # ---- Extract values ----
#         vals = getattr(embedding_obj, "values", None)
#         if not vals:
#             logger.error("❌ Gemini returned empty `.embedding.values`")
#             return [0.0] * _DIMENSION

#         floats = [float(v) for v in vals]

#         # ---- Normalize dimension ----
#         if len(floats) != _DIMENSION:
#             logger.warning(
#                 f"Embedding length {len(floats)} != { _DIMENSION }, padding/truncating"
#             )
#             if len(floats) > _DIMENSION:
#                 floats = floats[:_DIMENSION]
#             else:
#                 floats += [0.0] * (_DIMENSION - len(floats))

#         return floats

#     except Exception as e:
#         logger.error(f"🔥 Gemini embedding error: {e}")
#         raise RuntimeError(f"Gemini embedding error: {e}")


# async def embed_documents(texts: List[str]) -> List[List[float]]:
#     """Batch-embed multiple strings (Gemini has no batch API)."""
#     logger.info(f"Embedding {len(texts)} chunks via Gemini text-embedding-004")

#     vectors: List[List[float]] = []

#     for t in texts:
#         attempt = 0
#         while True:
#             try:
#                 vec = await embed_text(t)
#                 vectors.append(vec)
#                 break
#             except Exception as e:
#                 if attempt >= 2:
#                     logger.error("❌ Max retries reached for embedding.")
#                     raise

#                 backoff = 2 ** attempt
#                 logger.warning(
#                     f"⚠️ Retry {attempt+1} for Gemini embedding in {backoff}s — Error: {e}"
#                 )
#                 await asyncio.sleep(backoff)
#                 attempt += 1

#         await asyncio.sleep(0.05)  # Gentle rate-limit spacing

#     return vectors

# """
# Gemini Embeddings Module (Jan 2025 SDK)
# Uses models/text-embedding-004 via client.models.embed_content()
# """

# import os
# import logging
# import asyncio
# from typing import List

# from google import genai

# logger = logging.getLogger(__name__)

# GEMINI_EMBED_MODEL = "models/text-embedding-004"
# _DIMENSION = 768

# _client: genai.Client | None = None


# def _get_client() -> genai.Client:
#     """Create a singleton Gemini client."""
#     global _client
#     if _client is None:
#         api_key = os.getenv("GEMINI_API_KEY")
#         if not api_key:
#             raise ValueError("GEMINI_API_KEY must be set for embeddings")
#         _client = genai.Client(api_key=api_key)
#     return _client


# async def embed_text(text: str) -> List[float]:
#     """Embed one string using Gemini text-embedding-004."""
#     try:
#         client = _get_client()

#         # CORRECT Jan 2025 format — must wrap text inside `contents=[{parts:[{text:"..."}]}]`
#         res = await asyncio.to_thread(
#             client.models.embed_content,
#             model=GEMINI_EMBED_MODEL,
#             contents=[{
#                 "parts": [{
#                     "text": text or ""
#                 }]
#             }]
#         )

#         # Extract embedding object
#         embedding_obj = getattr(res, "embedding", None)
#         if embedding_obj is None:
#             logger.error("❌ Gemini returned no `.embedding` field")
#             return [0.0] * _DIMENSION

#         # Extract actual vector values
#         vals = getattr(embedding_obj, "values", None)
#         if not vals:
#             logger.error("❌ Empty `.embedding.values` from Gemini")
#             return [0.0] * _DIMENSION

#         floats = [float(v) for v in vals]

#         # Normalize to exact dimension
#         if len(floats) != _DIMENSION:
#             logger.warning(
#                 f"Embedding dim {len(floats)} != {_DIMENSION}, padding/truncating."
#             )
#             if len(floats) > _DIMENSION:
#                 floats = floats[:_DIMENSION]
#             else:
#                 floats += [0.0] * (_DIMENSION - len(floats))

#         return floats

#     except Exception as e:
#         logger.error(f"🔥 Gemini embedding error: {e}")
#         raise RuntimeError(f"Gemini embedding error: {e}")


# async def embed_documents(texts: List[str]) -> List[List[float]]:
#     """Batch embed multiple texts (manual batching)."""
#     logger.info(f"Embedding {len(texts)} chunks using Gemini {GEMINI_EMBED_MODEL}")

#     vectors: List[List[float]] = []

#     for t in texts:
#         attempt = 0
#         while True:
#             try:
#                 vec = await embed_text(t)
#                 vectors.append(vec)
#                 break
#             except Exception as e:
#                 if attempt >= 2:
#                     logger.error("❌ Max retries reached for embedding.")
#                     raise

#                 backoff = 2 ** attempt
#                 logger.warning(
#                     f"⚠️ Retry {attempt+1} in {backoff}s — Error: {e}"
#                 )
#                 await asyncio.sleep(backoff)
#                 attempt += 1

#         await asyncio.sleep(0.05)  # Gentle spacing to avoid rate-limit bursts

#     return vectors

"""
Gemini Embeddings Module (Jan 2025 SDK)
Uses models/text-embedding-004 via client.models.embed_content()
"""

import os
import logging
import asyncio
from typing import List, Optional
from google import genai

logger = logging.getLogger(__name__)

GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
_DIMENSION = int(os.getenv("PINECONE_DIMENSION", "3072"))

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Create a singleton Gemini client."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be set for embeddings")
        _client = genai.Client(api_key=api_key)
    return _client


async def embed_text(text: str) -> List[float]:
    """Embed a single string using Gemini text-embedding-004."""

    try:
        client = _get_client()

        # Use SDK signature supported in this environment: contents=<string>
        res = await asyncio.to_thread(
            client.models.embed_content,
            model=GEMINI_EMBED_MODEL,
            contents=(text or "")
        )

        # ---- Extract embedding (support both shapes) ----
        values = None

        # Shape A: res.embeddings[0].values
        emb_list = getattr(res, "embeddings", None)
        if emb_list and isinstance(emb_list, (list, tuple)) and len(emb_list) > 0:
            values = getattr(emb_list[0], "values", None)

        # Shape B: res.embedding.values
        if values is None:
            embedding = getattr(res, "embedding", None)
            if embedding is not None:
                values = getattr(embedding, "values", None)

        if not values:
            logger.error("❌ No embedding values found in Gemini response")
            return [0.0] * _DIMENSION

        floats = [float(v) for v in values]

        # Normalize dim
        if len(floats) != _DIMENSION:
            logger.warning(
                f"Embedding dim {len(floats)} != {_DIMENSION}; fixing."
            )
            if len(floats) > _DIMENSION:
                floats = floats[:_DIMENSION]
            else:
                floats += [0.0] * (_DIMENSION - len(floats))

        return floats

    except Exception as e:
        logger.error(f"🔥 Gemini embedding error: {e}")
        raise RuntimeError(f"Gemini embedding error: {e}")


async def embed_documents(texts: List[str]) -> List[List[float]]:
    """Manual multi-embedding loop."""
    logger.info(f"Embedding {len(texts)} chunks via {GEMINI_EMBED_MODEL}")

    vectors: List[List[float]] = []

    for t in texts:
        attempt = 0
        while True:
            try:
                vec = await embed_text(t)
                vectors.append(vec)
                break
            except Exception as e:
                attempt += 1
                if attempt > 2:
                    logger.error("❌ Max retries reached.")
                    raise

                backoff = 2 ** (attempt - 1)
                logger.warning(f"⚠️ Retry {attempt} in {backoff}s — {e}")
                await asyncio.sleep(backoff)

        await asyncio.sleep(0.05)

    return vectors
