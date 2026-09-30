"""
Embedding service using sentence-transformers (multilingual).
Model: paraphrase-multilingual-mpnet-base-v2 (768-dim, supports Indonesian)
"""
from functools import lru_cache
from app.config import settings


@lru_cache()
def _get_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.EMBEDDING_MODEL)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns list of float vectors."""
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)
    return embeddings.tolist()


async def embed_single(text: str) -> list[float]:
    return (await embed_texts([text]))[0]
