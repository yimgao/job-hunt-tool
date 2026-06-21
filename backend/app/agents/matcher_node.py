"""Matcher Node — Gemini 初筛 + GPT-4o-mini 深度分析，内置 retry。"""
from __future__ import annotations

import logging

from app.agents.state import AgentState
from app.services.matcher import MatcherService

logger = logging.getLogger(__name__)


async def matcher_node(state: AgentState) -> dict:
    """对 state.current_job 执行匹配分析，写入 match_report。

    MatcherService.quick_scan 已内置 retry + Gemini→OpenAI fallback。
    """
    job = state.get("current_job")
    resume_text = state.get("resume_text", "")

    if not job:
        return {"pipeline_status": "skip", "match_report": None}

    jd_text = job.get("jd_text", "")
    if not resume_text or not jd_text:
        return {"pipeline_status": "skip", "match_report": None}

    try:
        service = MatcherService()
        report, cost = await service.match(resume_text, jd_text)
        report_dict = report.model_dump()
        report_dict["job_id"] = str(job.get("id", ""))
        report_dict["llm_cost"] = cost

        score = report.match_score
        if score < 0.3:
            status = "skip"
        elif score < 0.6:
            status = "notify"
        else:
            status = "tailor"

        logger.info("matcher_node: score=%.2f → %s (cost=$%.6f)", score, status, cost)
        return {"match_report": report_dict, "pipeline_status": status}

    except Exception as exc:
        logger.error("matcher_node failed after retries: %s", exc)
        errors = list(state.get("errors", []))
        return {
            "errors": errors + [f"matcher: {exc}"],
            "match_report": None,
            "pipeline_status": "skip",
        }
