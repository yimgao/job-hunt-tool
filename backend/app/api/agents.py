"""POST /api/agents/run|batch — 触发智能体流水线。"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.agents.matcher_node import matcher_node
from app.agents.orchestrator import graph
from app.agents.scraper_node import scraper_node
from app.agents.state import AgentState
from app.agents.tailor_node import tailor_node
from app.agents.tracker_node import tracker_node
from app.api.deps import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["agents"])


class AgentRunRequest(BaseModel):
    resume_text: str = Field(min_length=50, description="简历全文")
    keywords: list[str] = Field(
        default_factory=lambda: ["Python", "Backend"],
        description="职位搜索关键词",
    )


class AgentRunResponse(BaseModel):
    pipeline_status: str
    jobs_found: int
    errors: list[str]
    match_report: dict | None = None
    tailored_resume: str | None = None


class BatchRunRequest(BaseModel):
    resume_text: str = Field(min_length=50)
    keywords: list[str] = Field(default_factory=lambda: ["Python", "Backend"])
    max_jobs: int = Field(default=5, ge=1, le=20, description="每次批量处理的最大 job 数")
    min_score: float = Field(default=0.3, ge=0.0, le=1.0, description="最低匹配分数才做 tailor")


class JobResult(BaseModel):
    title: str
    company: str
    match_score: float | None
    status: str
    application_id: str | None


class BatchRunResponse(BaseModel):
    jobs_scraped: int
    jobs_processed: int
    results: list[JobResult]
    errors: list[str]


@router.post("/agents/run", response_model=AgentRunResponse, dependencies=[Depends(verify_api_key)])
async def run_pipeline(req: AgentRunRequest) -> AgentRunResponse:
    """触发一次完整求职流水线（单 job）: 爬取 → 匹配 → 定制 → 追踪。"""
    initial_state: AgentState = {
        "resume_text": req.resume_text,
        "jobs": [],
        "pipeline_status": "init",
        "errors": [],
    }
    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}")

    return AgentRunResponse(
        pipeline_status=final_state.get("pipeline_status", "unknown"),
        jobs_found=len(final_state.get("jobs", [])),
        errors=final_state.get("errors", []),
        match_report=final_state.get("match_report"),
        tailored_resume=final_state.get("tailored_resume"),
    )


@router.post("/agents/batch", response_model=BatchRunResponse, dependencies=[Depends(verify_api_key)])
async def batch_pipeline(req: BatchRunRequest) -> BatchRunResponse:
    """批量处理多个职位: 爬取一次 → 对 top-N job 分别匹配/定制/追踪。

    每次调用只爬一次（成本固定），对 max_jobs 个去重 job 并发做匹配，
    高匹配（≥ min_score）串行做 tailor + tracker。
    """
    all_errors: list[str] = []
    results: list[JobResult] = []

    # ── Step 1: Scrape ────────────────────────────────────────────────────────
    initial_state: AgentState = {
        "resume_text": req.resume_text,
        "jobs": [],
        "pipeline_status": "init",
        "errors": [],
    }
    scrape_state = await scraper_node(initial_state)
    all_jobs: list[dict] = scrape_state.get("jobs", [])
    user_id: str | None = scrape_state.get("user_id")
    all_errors.extend(scrape_state.get("errors", []))

    if not all_jobs:
        return BatchRunResponse(jobs_scraped=0, jobs_processed=0, results=[], errors=all_errors)

    candidate_jobs = all_jobs[: req.max_jobs]

    # ── Step 2: Match all candidates concurrently ─────────────────────────────
    async def match_one(job: dict) -> dict:
        state: AgentState = {
            "resume_text": req.resume_text,
            "jobs": [],
            "current_job": job,
            "user_id": user_id,
            "pipeline_status": "scraped",
            "errors": [],
        }
        return await matcher_node(state)

    match_states = await asyncio.gather(*[match_one(j) for j in candidate_jobs], return_exceptions=True)

    # ── Step 3: Tailor high matches + track all ───────────────────────────────
    for job, match_state in zip(candidate_jobs, match_states):
        if isinstance(match_state, Exception):
            logger.warning("batch: matcher error for %s: %s", job.get("title"), match_state)
            all_errors.append(f"matcher: {match_state}")
            results.append(JobResult(title=job.get("title", ""), company=job.get("company", ""),
                                     match_score=None, status="error", application_id=None))
            continue

        score: float | None = None
        report = match_state.get("match_report")
        if report:
            score = report.get("match_score")

        pipeline_status = match_state.get("pipeline_status", "skip")
        tailor_state: dict = {}

        if score is not None and score >= req.min_score and pipeline_status in ("tailor", "notify"):
            tstate: AgentState = {
                "resume_text": req.resume_text,
                "jobs": [],
                "current_job": job,
                "match_report": report,
                "user_id": user_id,
                "pipeline_status": pipeline_status,
                "errors": [],
            }
            tailor_state = await tailor_node(tstate)

        track_state: AgentState = {
            "resume_text": req.resume_text,
            "jobs": [],
            "current_job": job,
            "match_report": report,
            "cover_letter": tailor_state.get("cover_letter"),
            "user_id": user_id,
            "pipeline_status": tailor_state.get("pipeline_status") or pipeline_status,
            "errors": [],
        }
        tracked = await tracker_node(track_state)

        results.append(JobResult(
            title=job.get("title", ""),
            company=job.get("company", ""),
            match_score=score,
            status=tracked.get("pipeline_status", "tracked"),
            application_id=tracked.get("application_id"),
        ))

    return BatchRunResponse(
        jobs_scraped=len(all_jobs),
        jobs_processed=len(candidate_jobs),
        results=results,
        errors=all_errors,
    )
