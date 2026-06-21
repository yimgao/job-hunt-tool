"""Tailor Node — Structured Outputs 简历定制。"""
from __future__ import annotations

import logging

from app.agents.state import AgentState
from app.services.tailor import TailorService

logger = logging.getLogger(__name__)


async def tailor_node(state: AgentState) -> dict:
    """定制简历，输出写入 tailored_resume + cover_letter。"""
    job = state.get("current_job")
    resume_text = state.get("resume_text", "")

    if not job or not resume_text:
        return {"pipeline_status": "skip"}

    jd_text = job.get("jd_text", "")
    job_title = job.get("title", "")

    try:
        service = TailorService()
        output = await service.tailor(resume_text, jd_text, job_title)
        logger.info(
            "tailor_node: %d key changes, %d keywords",
            len(output.key_changes),
            len(output.match_keywords),
        )
        return {
            "tailored_resume": output.tailored_resume,
            "cover_letter": output.cover_letter,
            "pipeline_status": "tailored",
        }

    except Exception as exc:
        logger.error("tailor_node failed: %s", exc)
        errors = list(state.get("errors", []))
        return {
            "errors": errors + [f"tailor: {exc}"],
            "tailored_resume": resume_text,
            "pipeline_status": "tailored",
        }
