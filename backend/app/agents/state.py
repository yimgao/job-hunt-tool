"""AgentState — LangGraph 图状态定义。"""
from __future__ import annotations
from typing import Any
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """全局流水线状态，在各 node 之间传递。"""
    resume_text: str
    jobs: list[dict[str, Any]]
    current_job: dict[str, Any] | None
    match_report: dict[str, Any] | None
    tailored_resume: str | None
    cover_letter: str | None
    application_id: str | None
    pipeline_status: str
    errors: list[str]
