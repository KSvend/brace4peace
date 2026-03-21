import pytest
from backend.tools.embed import chunk_text


def test_chunk_text_splits_at_target_size():
    text = "Sentence one. " * 100
    chunks = chunk_text(text, max_tokens=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.split()) <= 120


def test_chunk_text_preserves_all_content():
    text = "Alpha. Bravo. Charlie. Delta. Echo."
    chunks = chunk_text(text, max_tokens=500)
    joined = " ".join(chunks)
    assert "Alpha" in joined
    assert "Echo" in joined


def test_chunk_text_single_short_text():
    text = "Short text."
    chunks = chunk_text(text, max_tokens=500)
    assert len(chunks) == 1
    assert chunks[0] == "Short text."


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_generate_embedding_returns_384_dims(mocker):
    import numpy as np
    mock_model = mocker.patch("backend.tools.embed._get_model")
    mock_model.return_value.encode.return_value = np.array([0.1] * 384)
    from backend.tools.embed import generate_embedding
    result = generate_embedding("test text")
    assert len(result) == 384
