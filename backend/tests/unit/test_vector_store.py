"""Tests for VectorStore — embed, add_chunk, chunk_resume, search."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


FAKE_EMBEDDING = [0.1] * 1536


@pytest.fixture()
def mock_db():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture()
def vector_store(mock_db):
    from app.services.vector_store import VectorStore
    return VectorStore(db_session=mock_db)


@pytest.mark.asyncio
async def test_embed_returns_vector(vector_store):
    mock_resp = MagicMock()
    mock_resp.data = [MagicMock(embedding=FAKE_EMBEDDING)]
    vector_store.client = AsyncMock()
    vector_store.client.embeddings.create = AsyncMock(return_value=mock_resp)

    vec = await vector_store.embed("Python developer with 5 years experience")
    assert len(vec) == 1536
    assert vec[0] == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_embed_falls_back_to_zero_on_error(vector_store):
    vector_store.client = AsyncMock()
    vector_store.client.embeddings.create = AsyncMock(side_effect=RuntimeError("API down"))

    vec = await vector_store.embed("some text")
    assert all(v == 0.0 for v in vec)


@pytest.mark.asyncio
async def test_add_chunk_persists(vector_store, mock_db):
    import uuid

    user_uuid = str(uuid.uuid4())

    async def fake_refresh(obj):
        obj.id = uuid.uuid4()

    mock_db.refresh = fake_refresh

    with patch.object(vector_store, "embed", new=AsyncMock(return_value=FAKE_EMBEDDING)):
        result = await vector_store.add_chunk(
            user_uuid, "experience", "Led backend engineering at Acme Corp for 4 years."
        )

    assert "chunk_id" in result
    assert result["embedding_dim"] == 1536
    assert mock_db.add.called
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_chunk_resume_splits_text(vector_store):
    # double-newline separated paragraphs, each >50 chars
    long_resume = (
        "Alice Smith is a senior software engineer with 8 years of experience.\n\n"
        "She has worked at Google, Meta, and Stripe building distributed systems.\n\n"
        "Her skills include Python, Go, Kubernetes, PostgreSQL, and Redis at scale.\n\n"
        "Education: BS Computer Science Stanford University class of 2016 with honors."
    )
    chunks = await vector_store.chunk_resume(long_resume)
    assert isinstance(chunks, list)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) > 0


@pytest.mark.asyncio
async def test_chunk_resume_short_paragraphs_filtered(vector_store):
    # Short paragraphs (<=50 chars) are filtered out
    text = "Short.\n\nAlso short.\n\nThis is a longer paragraph that exceeds the fifty character minimum limit."
    chunks = await vector_store.chunk_resume(text)
    assert isinstance(chunks, list)
    assert len(chunks) == 1
    assert "fifty character" in chunks[0]
