"""POST /api/match 端点集成测试。"""
from __future__ import annotations

import pytest

RESUME = "Python developer with 5 years experience in FastAPI and PostgreSQL. " * 5
JD = "We are looking for a Python backend engineer with FastAPI experience. " * 5


class TestHealth:
    async def test_health_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestMatchEndpoint:
    async def test_valid_request_returns_200(self, client):
        resp = await client.post(
            "/api/match",
            json={"resume_text": RESUME, "jd_text": JD},
        )
        assert resp.status_code == 200

    async def test_response_has_required_fields(self, client):
        resp = await client.post(
            "/api/match",
            json={"resume_text": RESUME, "jd_text": JD},
        )
        body = resp.json()
        assert "report" in body
        assert "report_id" in body
        assert "llm_model" in body
        assert "llm_cost" in body

    async def test_report_id_is_uuid(self, client):
        import uuid
        resp = await client.post(
            "/api/match",
            json={"resume_text": RESUME, "jd_text": JD},
        )
        report_id = resp.json()["report_id"]
        uuid.UUID(report_id)  # raises if not valid UUID

    async def test_report_has_dimensions(self, client):
        resp = await client.post(
            "/api/match",
            json={"resume_text": RESUME, "jd_text": JD},
        )
        dims = resp.json()["report"]["dimensions"]
        for field in ("skills_match", "experience_match", "industry_match", "culture_fit"):
            assert field in dims
            assert 0.0 <= dims[field] <= 1.0

    async def test_short_resume_returns_422(self, client):
        resp = await client.post(
            "/api/match",
            json={"resume_text": "short", "jd_text": JD},
        )
        assert resp.status_code == 422

    async def test_short_jd_returns_422(self, client):
        resp = await client.post(
            "/api/match",
            json={"resume_text": RESUME, "jd_text": "tiny"},
        )
        assert resp.status_code == 422

    async def test_missing_body_returns_422(self, client):
        resp = await client.post("/api/match", json={})
        assert resp.status_code == 422
