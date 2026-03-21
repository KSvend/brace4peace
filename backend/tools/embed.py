"""Text chunking, embedding generation, and pgvector storage."""
import re

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from backend.config import EMBEDDING_MODEL
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def chunk_text(text: str, max_tokens: int = 500) -> list[str]:
    if not text.strip():
        return []
    paragraphs = re.split(r"\n\n+", text.strip())
    chunks = []
    current_chunk = []
    current_size = 0
    for para in paragraphs:
        para_words = len(para.split())
        if current_size + para_words <= max_tokens:
            current_chunk.append(para)
            current_size += para_words
        else:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
            if para_words > max_tokens:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                sent_chunk = []
                sent_size = 0
                for sent in sentences:
                    sw = len(sent.split())
                    if sent_size + sw <= max_tokens:
                        sent_chunk.append(sent)
                        sent_size += sw
                    else:
                        if sent_chunk:
                            chunks.append(" ".join(sent_chunk))
                        sent_chunk = [sent]
                        sent_size = sw
                if sent_chunk:
                    chunks.append(" ".join(sent_chunk))
                current_chunk = []
                current_size = 0
            else:
                current_chunk = [para]
                current_size = para_words
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    return chunks


def generate_embedding(text: str) -> list[float]:
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_and_store(text: str, metadata: dict, client=None) -> list[str]:
    if client is None:
        from backend.db import get_client
        client = get_client()
    chunks = chunk_text(text)
    chunk_ids = []
    for i, chunk in enumerate(chunks):
        embedding = generate_embedding(chunk)
        row = {
            "source_id": metadata.get("source_id"),
            "tier": metadata.get("tier", "full_text"),
            "content": chunk,
            "chunk_index": i,
            "embedding": embedding,
            "country": metadata.get("country", []),
            "theme": metadata.get("theme", []),
            "classification": metadata.get("classification"),
            "date_published": metadata.get("date_published"),
            "verified": metadata.get("verified", False),
        }
        result = client.table("document_chunks").insert(row).execute()
        if result.data:
            chunk_ids.append(result.data[0]["id"])
    return chunk_ids
