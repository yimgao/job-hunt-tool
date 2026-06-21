"""Chrome Extension API — /api/ext/*"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.extension import (
    CompleteTaskRequest,
    CreateTaskRequest,
    ExtensionTask,
)
from app.services import task_store

router = APIRouter(prefix="/api/ext", tags=["extension"])


@router.post("/task", response_model=ExtensionTask, status_code=201)
async def create_task(req: CreateTaskRequest) -> ExtensionTask:
    """创建 Extension 任务（手动或外部调用，applicant_node 直接走 task_store）。"""
    task = task_store.create_task(
        job_title=req.job_title,
        company=req.company,
        apply_url=req.apply_url,
        application_id=req.application_id,
        prefill_data=req.prefill_data,
    )
    return task


@router.get("/task/{task_id}", response_model=ExtensionTask)
async def get_task(task_id: str) -> ExtensionTask:
    """查询单个任务详情（Extension popup 拉取预填数据用）。"""
    task = task_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks/pending", response_model=list[ExtensionTask])
async def list_pending_tasks() -> list[ExtensionTask]:
    """Extension 轮询接口 — 返回所有 pending 任务。"""
    return task_store.get_pending()


@router.post("/complete", response_model=ExtensionTask)
async def complete_task(req: CompleteTaskRequest) -> ExtensionTask:
    """Extension 投递完成后回调 — 更新任务状态。"""
    updated = task_store.update_status(req.task_id, req.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated
