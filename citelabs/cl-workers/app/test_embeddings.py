from fastapi import APIRouter
from pydantic import BaseModel
from app.embeddings_gemini import embed_text

router = APIRouter()

class EmbedRequest(BaseModel):
    text: str

@router.post("/test/embedding")
async def test_single_embedding(req: EmbedRequest):
    vec = await embed_text(req.text)
    return {
        "dim": len(vec),
        "vector_preview": vec[:10]
    }
