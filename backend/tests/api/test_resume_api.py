"""Tests for /api/resume/* endpoints."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


ADD_CHUNK_RESULT = {"chunk_id": "chunk-abc-123", "embedding_dim": 1536}


@pytest.fixture(autouse=True)
def mock_vector_store():
    with patch("app.api.resume.VectorStore") as mock_cls:
        instance = AsyncMock()
        instance.add_chunk = AsyncMock(return_value=ADD_CHUNK_RESULT)
        instance.chunk_resume = AsyncMock(
            return_value=["Experience: built APIs at Scale Inc for 3 years managing large datasets."]
        )
        mock_cls.return_value = instance
        yield instance


@pytest.mark.asyncio
async def test_add_single_chunk(client):
    resp = await client.post(
        "/api/resume/chunks",
        json={
            "user_id": "user-001",
            "chunk_type": "experience",
            "content": "Led backend team at Acme Corp, built REST APIs serving 10M requests/day.",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["chunk_id"] == "chunk-abc-123"
    assert data["embedding_dim"] == 1536
    assert data["message"] == "chunk added"


@pytest.mark.asyncio
async def test_add_chunk_invalid_type(client):
    resp = await client.post(
        "/api/resume/chunks",
        json={
            "user_id": "user-001",
            "chunk_type": "invalid_type",
            "content": "Some valid content that is long enough to pass validation.",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_chunk_content_too_short(client):
    resp = await client.post(
        "/api/resume/chunks",
        json={
            "user_id": "user-001",
            "chunk_type": "skill",
            "content": "short",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ingest_full_resume(client):
    resume_text = (
        "Alice Smith — Software Engineer\n"
        "5 years experience building distributed systems.\n"
        "Experience: Led teams at Google and Meta.\n"
        "Skills: Python, Go, Kubernetes, PostgreSQL, Redis.\n"
        "Education: BS Computer Science, Stanford 2019.\n"
    )
    resp = await client.post(
        "/api/resume/ingest",
        json={"user_id": "user-002", "resume_text": resume_text},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["chunk_id"] == "chunk-abc-123"


@pytest.mark.asyncio
async def test_ingest_resume_too_short(client):
    resp = await client.post(
        "/api/resume/ingest",
        json={"user_id": "user-002", "resume_text": "Too short."},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_valid_chunk_types(client):
    for chunk_type in ["experience", "education", "project", "skill", "other"]:
        resp = await client.post(
            "/api/resume/chunks",
            json={
                "user_id": "user-001",
                "chunk_type": chunk_type,
                "content": "Valid content that meets the minimum length requirement for this field.",
            },
        )
        assert resp.status_code == 201, f"chunk_type={chunk_type} failed: {resp.json()}"
