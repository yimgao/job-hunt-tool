"""内存任务存储 — Extension 任务队列。

Phase 3: 单进程内存字典，重启后丢失。
Phase 4: 迁移至 Redis（持久化 + 多进程安全）。
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone

from app.schemas.extension import ExtensionTask, PrefillData

_store: dict[str, ExtensionTask] = {}


def create_task(
    job_title: str,
    company: str,
    prefill_data: PrefillData,
    apply_url: str | None = None,
    application_id: str | None = None,
) -> ExtensionTask:
    task_id = str(uuid.uuid4())
    task = ExtensionTask(
        task_id=task_id,
        job_title=job_title,
        company=company,
        apply_url=apply_url,
        application_id=application_id,
        prefill_data=prefill_data,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    _store[task_id] = task
    return task


def get_task(task_id: str) -> ExtensionTask | None:
    return _store.get(task_id)


def get_pending() -> list[ExtensionTask]:
    return [t for t in _store.values() if t.status == "pending"]


def update_status(task_id: str, status: str) -> ExtensionTask | None:
    task = _store.get(task_id)
    if not task:
        return None
    _store[task_id] = task.model_copy(update={"status": status})
    return _store[task_id]


def clear() -> None:
    """测试用 — 清空全部任务。"""
    _store.clear()
