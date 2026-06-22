"""Tracker Node — 更新 application 状态，写入 DB。"""
from __future__ import annotations

import logging
import uuid

from app.agents.state import AgentState
from app.db.crud import upsert_application

logger = logging.getLogger(__name__)

_STATUS_MAP = {
    "skip": "scraped",
    "notify": "matched",
    "tailor": "matched",
    "tailored": "tailored",
    "applicant_ready": "tailored",
    "tracked:skip": "scraped",
    "tracked:notify": "matched",
    "tracked:tailored": "tailored",
    "tracked:applicant_ready": "tailored",
}


async def tracker_node(state: AgentState) -> dict:
    """记录 pipeline 最终状态到 applications 表。"""
    pipeline_status = state.get("pipeline_status", "unknown")
    match_report = state.get("match_report")
    job = state.get("current_job")
    user_id_str = state.get("user_id")

    if not job or not user_id_str:
        logger.warning("tracker_node: missing job or user_id — skipping DB write")
        return {"pipeline_status": f"tracked:{pipeline_status}"}

    # Resolve job DB UUID (set by scraper_node after bulk_upsert_jobs)
    job_db_id_str = job.get("db_id")
    if not job_db_id_str:
        logger.warning("tracker_node: job has no db_id — skipping DB write")
        return {"pipeline_status": f"tracked:{pipeline_status}"}

    try:
        job_id = uuid.UUID(job_db_id_str)
        user_id = uuid.UUID(user_id_str)
    except ValueError as exc:
        logger.error("tracker_node: invalid UUID: %s", exc)
        return {"pipeline_status": f"tracked:{pipeline_status}"}

    score = match_report.get("match_score") if match_report else None
    cover_letter = state.get("cover_letter")
    db_status = _STATUS_MAP.get(pipeline_status, "scraped")

    try:
        app_id = await upsert_application(
            job_id=job_id,
            user_id=user_id,
            status=db_status,
            match_score=score,
            match_report=match_report,
            cover_letter=cover_letter,
        )
        logger.info(
            "tracker_node: application %s (job=%s score=%s status=%s)",
            app_id, job_id, score, db_status,
        )
        return {
            "application_id": str(app_id),
            "pipeline_status": f"tracked:{pipeline_status}",
        }

    except Exception as exc:
        logger.error("tracker_node: DB write failed: %s", exc)
        errors = list(state.get("errors", []))
        return {
            "errors": errors + [f"tracker: {exc}"],
            "pipeline_status": f"tracked:{pipeline_status}",
        }
