"""Tracker Node — 更新 application 状态，推进漏斗。"""
from __future__ import annotations

import logging

from app.agents.state import AgentState

logger = logging.getLogger(__name__)


async def tracker_node(state: AgentState) -> dict:
    """记录 pipeline 最终状态。Phase 2 在内存中更新；Phase 3 写入 DB。"""
    status = state.get("pipeline_status", "unknown")
    match_report = state.get("match_report")
    job = state.get("current_job")

    job_id = str(job.get("id", "")) if job else "unknown"
    score = match_report.get("match_score", 0.0) if match_report else 0.0

    logger.info("tracker_node: job=%s score=%.2f final_status=%s", job_id, score, status)

    return {"pipeline_status": f"tracked:{status}"}
