"""Extension API schemas — task 创建、查询、完成。"""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class PrefillData(BaseModel):
    """Chrome Extension 预填数据。"""
    name: str = ""
    email: str = ""
    phone: str = ""
    resume_highlights: list[str] = Field(default_factory=list, description="简历亮点，用于 popup 展示")
    cover_letter: str = ""
    skills: list[str] = Field(default_factory=list)


class ExtensionTask(BaseModel):
    """Extension 任务 — 一次待投递的准备数据。"""
    task_id: str
    job_title: str
    company: str
    apply_url: str | None = None
    application_id: str | None = None
    prefill_data: PrefillData
    status: str = Field(default="pending", pattern="^(pending|filled|applied|skipped)$")
    created_at: datetime


class CreateTaskRequest(BaseModel):
    """POST /api/ext/task 请求体（供外部调用，applicant_node 走 task_store 直接创建）。"""
    job_title: str
    company: str
    apply_url: str | None = None
    application_id: str | None = None
    prefill_data: PrefillData


class CompleteTaskRequest(BaseModel):
    """POST /api/ext/complete 请求体。"""
    task_id: str
    status: str = Field(default="applied", pattern="^(applied|skipped)$")
    note: str | None = None
