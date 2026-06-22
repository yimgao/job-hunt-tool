"""Scraper Node — 爬取职位 + Redis L1 + TF-IDF L2 去重 + DB 持久化。"""
from __future__ import annotations

import logging

from app.agents.state import AgentState
from app.db.crud import bulk_upsert_jobs, get_or_create_default_user
from app.services.dedup import compute_content_hash, filter_duplicates, redis_cache
from app.services.scraper import ScraperService

logger = logging.getLogger(__name__)


async def scraper_node(state: AgentState) -> dict:
    """爬取新职位，去重后写入 DB 并更新状态。"""
    keywords = state.get("resume_text", "Python").split()[:5]
    service = ScraperService(keywords=keywords)

    try:
        raw_jobs = await service.scrape()
    except Exception as exc:
        logger.error("scraper_node failed: %s", exc)
        errors = list(state.get("errors", []))
        return {"errors": errors + [f"scraper: {exc}"], "jobs": [], "pipeline_status": "scrape_failed"}

    # Layer 1: Redis hash cache (O(1), async)
    redis_filtered: list[dict] = []
    for job in (j.to_dict() for j in raw_jobs):
        h = compute_content_hash(job.get("jd_text", ""))
        if await redis_cache.has(h):
            logger.debug("scraper_node: Redis cache hit for hash %s", h[:8])
        else:
            redis_filtered.append(job)

    if not redis_filtered:
        logger.info("scraper_node: all %d jobs already in Redis cache", len(raw_jobs))
        return {"jobs": state.get("jobs", []), "pipeline_status": "scraped"}

    # Layer 2: TF-IDF fuzzy dedup
    existing_jobs: list[dict] = state.get("jobs", [])
    existing_hashes = {j.get("content_hash", "") for j in existing_jobs if j.get("content_hash")}
    existing_texts = [j.get("jd_text", "") for j in existing_jobs]

    unique, dupes = filter_duplicates(redis_filtered, existing_hashes, existing_texts)

    # Update Redis with newly confirmed unique hashes
    new_hashes = [j["content_hash"] for j in unique if j.get("content_hash")]
    await redis_cache.add_many(new_hashes)

    logger.info(
        "scraper_node: %d new (redis_skip=%d, tfidf_dup=%d)",
        len(unique), len(raw_jobs) - len(redis_filtered), len(dupes),
    )

    # Persist all unique jobs to DB; attach DB id back to each job dict
    try:
        saved_ids = await bulk_upsert_jobs(unique)
        for job_dict, db_id in zip(unique, saved_ids):
            job_dict["db_id"] = str(db_id)
    except Exception as exc:
        logger.warning("scraper_node: DB persist failed (continuing): %s", exc)

    # Ensure default user exists (creates if needed)
    try:
        user_id = await get_or_create_default_user()
    except Exception as exc:
        logger.warning("scraper_node: could not get/create default user: %s", exc)
        user_id = None

    all_jobs = existing_jobs + unique
    return {
        "jobs": all_jobs,
        "current_job": unique[0] if unique else None,
        "user_id": str(user_id) if user_id else None,
        "pipeline_status": "scraped",
    }
