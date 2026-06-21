"""Applicant Node — 从定制简历构建 Extension 任务。

Phase 3: 无用户画像，name/email/phone 留空（Phase 4 接 users 表）。
"""
from __future__ import annotations
import logging

from app.agents.state import AgentState
from app.schemas.extension import PrefillData
from app.services import task_store

logger = logging.getLogger(__name__)


async def applicant_node(state: AgentState) -> dict:
    """将定制简历封装成 Extension 任务，推入任务队列。"""
    job = state.get("current_job")
    tailored_resume = state.get("tailored_resume") or ""
    cover_letter = state.get("cover_letter") or ""
    match_report = state.get("match_report") or {}

    if not job:
        logger.warning("applicant_node: no current_job in state, skipping")
        return {"pipeline_status": "tailored"}

    highlights: list[str] = match_report.get("strengths", [])[:5]
    skills: list[str] = list(match_report.get("dimensions", {}).keys())

    prefill = PrefillData(
        name="",
        email="",
        phone="",
        resume_highlights=highlights,
        cover_letter=cover_letter,
        skills=skills,
    )

    task = task_store.create_task(
        job_title=job.get("title", ""),
        company=job.get("company", ""),
        apply_url=job.get("url"),
        application_id=state.get("application_id"),
        prefill_data=prefill,
    )

    logger.info(
        "applicant_node: created task %s for %s @ %s",
        task.task_id,
        task.job_title,
        task.company,
    )
    return {"application_id": task.task_id, "pipeline_status": "applicant_ready"}
