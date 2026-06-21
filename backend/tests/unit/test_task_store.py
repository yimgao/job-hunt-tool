"""task_store 单元测试。"""
from __future__ import annotations
import pytest
from app.schemas.extension import PrefillData
from app.services import task_store


@pytest.fixture(autouse=True)
def reset_store():
    task_store.clear()
    yield
    task_store.clear()


def _make_prefill(**kwargs) -> PrefillData:
    return PrefillData(
        name=kwargs.get("name", ""),
        email=kwargs.get("email", "test@example.com"),
        resume_highlights=["Python", "FastAPI"],
        cover_letter="Dear Hiring Manager...",
        skills=["python", "fastapi"],
    )


class TestCreateTask:
    def test_creates_with_pending_status(self):
        t = task_store.create_task("Engineer", "ACME", _make_prefill())
        assert t.status == "pending"
        assert t.task_id

    def test_stored_in_memory(self):
        t = task_store.create_task("Engineer", "ACME", _make_prefill())
        fetched = task_store.get_task(t.task_id)
        assert fetched is not None
        assert fetched.task_id == t.task_id

    def test_multiple_tasks(self):
        task_store.create_task("Job A", "Company A", _make_prefill())
        task_store.create_task("Job B", "Company B", _make_prefill())
        assert len(task_store.get_pending()) == 2


class TestGetPending:
    def test_only_pending_returned(self):
        t1 = task_store.create_task("Job A", "Co A", _make_prefill())
        t2 = task_store.create_task("Job B", "Co B", _make_prefill())
        task_store.update_status(t1.task_id, "applied")

        pending = task_store.get_pending()
        assert len(pending) == 1
        assert pending[0].task_id == t2.task_id

    def test_empty_when_none(self):
        assert task_store.get_pending() == []


class TestUpdateStatus:
    def test_applied(self):
        t = task_store.create_task("Job", "Co", _make_prefill())
        updated = task_store.update_status(t.task_id, "applied")
        assert updated is not None
        assert updated.status == "applied"

    def test_skipped(self):
        t = task_store.create_task("Job", "Co", _make_prefill())
        updated = task_store.update_status(t.task_id, "skipped")
        assert updated.status == "skipped"

    def test_not_found_returns_none(self):
        result = task_store.update_status("no-such-id", "applied")
        assert result is None
