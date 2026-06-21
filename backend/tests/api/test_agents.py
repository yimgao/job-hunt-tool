"""POST /api/agents/run 端点测试。"""
from __future__ import annotations

RESUME = "Python developer with 5 years experience in FastAPI, PostgreSQL, and Redis. " * 5


class TestAgentsRunEndpoint:
    async def test_valid_run_returns_200(self, client):
        resp = await client.post(
            "/api/agents/run",
            json={"resume_text": RESUME, "keywords": ["Python", "FastAPI"]},
        )
        assert resp.status_code == 200

    async def test_response_has_required_fields(self, client):
        resp = await client.post(
            "/api/agents/run",
            json={"resume_text": RESUME},
        )
        body = resp.json()
        assert "pipeline_status" in body
        assert "jobs_found" in body
        assert "errors" in body

    async def test_jobs_found_greater_than_zero(self, client):
        resp = await client.post(
            "/api/agents/run",
            json={"resume_text": RESUME},
        )
        assert resp.json()["jobs_found"] > 0

    async def test_short_resume_returns_422(self, client):
        resp = await client.post(
            "/api/agents/run",
            json={"resume_text": "short"},
        )
        assert resp.status_code == 422
