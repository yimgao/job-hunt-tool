"""POST /api/agents/run — 触发智能体流水线。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.orchestrator import graph
from app.agents.state import AgentState

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


@router.post("/agents/run", response_model=AgentRunResponse)
async def run_pipeline(req: AgentRunRequest) -> AgentRunResponse:
    """触发一次完整的求职流水线: 爬取 → 匹配 → 定制。

    注意: Phase 2 是同步单次运行；Phase 3 改为后台异步任务队列。
    """
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
