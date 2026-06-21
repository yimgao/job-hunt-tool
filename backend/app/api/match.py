"""POST /api/match — 简历 vs JD 匹配分析（Phase 1 MVP）。"""
from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from app.schemas.match import MatchRequest, MatchResponse
from app.services.matcher import MatcherService

router = APIRouter(prefix="/api", tags=["match"])


@router.post("/match", response_model=MatchResponse)
async def match_job(req: MatchRequest):
    """简历与 JD 匹配分析。

    接收简历全文和 JD 全文，返回结构化匹配报告。
    支持 RAG 召回（若 VectorStore 已配置）。
    """
    try:
        service = MatcherService()
        report, cost = await service.match(req.resume_text, req.jd_text)
        return MatchResponse(
            report=report,
            report_id=str(uuid.uuid4()),
            llm_model=service.llm_model,
            llm_cost=round(cost, 6),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
