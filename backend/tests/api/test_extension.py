"""Extension API 端点测试。"""
from __future__ import annotations
import pytest
from app.services import task_store

PREFILL = {
    "name": "Alice",
    "email": "alice@example.com",
    "phone": "555-1234",
    "resume_highlights": ["Python expert", "FastAPI"],
    "cover_letter": "Dear Hiring Manager, I am excited...",
    "skills": ["python", "fastapi", "postgresql"],
}


@pytest.fixture(autouse=True)
def reset():
    task_store.clear()
    yield
    task_store.clear()


class TestCreateTask:
    async def test_returns_201(self, client):
        resp = await client.post(
            "/api/ext/task",
            json={"job_title": "Backend Eng", "company": "ACME", "prefill_data": PREFILL},
        )
        assert resp.status_code == 201

    async def test_response_has_task_id(self, client):
        resp = await client.post(
            "/api/ext/task",
            json={"job_title": "Backend Eng", "company": "ACME", "prefill_data": PREFILL},
        )
        body = resp.json()
        assert "task_id" in body
        assert body["status"] == "pending"

    async def test_prefill_data_preserved(self, client):
        resp = await client.post(
            "/api/ext/task",
            json={"job_title": "SWE", "company": "Corp", "prefill_data": PREFILL},
        )
        prefill = resp.json()["prefill_data"]
        assert prefill["email"] == "alice@example.com"
        assert "Python expert" in prefill["resume_highlights"]


class TestGetTask:
    async def test_get_existing(self, client):
        create = await client.post(
            "/api/ext/task",
            json={"job_title": "SWE", "company": "Corp", "prefill_data": PREFILL},
        )
        task_id = create.json()["task_id"]
        resp = await client.get(f"/api/ext/task/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["task_id"] == task_id

    async def test_get_nonexistent_returns_404(self, client):
        resp = await client.get("/api/ext/task/nonexistent-id")
        assert resp.status_code == 404


class TestListPending:
    async def test_empty_initially(self, client):
        resp = await client.get("/api/ext/tasks/pending")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_shows_pending_tasks(self, client):
        await client.post(
            "/api/ext/task",
            json={"job_title": "SWE", "company": "Corp", "prefill_data": PREFILL},
        )
        resp = await client.get("/api/ext/tasks/pending")
        assert len(resp.json()) == 1

    async def test_completed_tasks_excluded(self, client):
        create = await client.post(
            "/api/ext/task",
            json={"job_title": "SWE", "company": "Corp", "prefill_data": PREFILL},
        )
        task_id = create.json()["task_id"]
        await client.post("/api/ext/complete", json={"task_id": task_id, "status": "applied"})

        resp = await client.get("/api/ext/tasks/pending")
        assert resp.json() == []


class TestCompleteTask:
    async def test_applied(self, client):
        create = await client.post(
            "/api/ext/task",
            json={"job_title": "SWE", "company": "Corp", "prefill_data": PREFILL},
        )
        task_id = create.json()["task_id"]
        resp = await client.post(
            "/api/ext/complete", json={"task_id": task_id, "status": "applied"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "applied"

    async def test_skipped(self, client):
        create = await client.post(
            "/api/ext/task",
            json={"job_title": "SWE", "company": "Corp", "prefill_data": PREFILL},
        )
        task_id = create.json()["task_id"]
        resp = await client.post(
            "/api/ext/complete", json={"task_id": task_id, "status": "skipped"}
        )
        assert resp.json()["status"] == "skipped"

    async def test_nonexistent_task_404(self, client):
        resp = await client.post(
            "/api/ext/complete", json={"task_id": "no-such", "status": "applied"}
        )
        assert resp.status_code == 404

    async def test_invalid_status_422(self, client):
        create = await client.post(
            "/api/ext/task",
            json={"job_title": "SWE", "company": "Corp", "prefill_data": PREFILL},
        )
        task_id = create.json()["task_id"]
        resp = await client.post(
            "/api/ext/complete", json={"task_id": task_id, "status": "invalid"}
        )
        assert resp.status_code == 422
