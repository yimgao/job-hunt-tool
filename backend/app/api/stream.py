"""POST /api/agents/stream — SSE 流式 pipeline 进度。"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.orchestrator import graph
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agents"])

NODE_LABELS: dict[str, str] = {
    "scraper": "Scraping job listings…",
    "matcher": "Analyzing match score…",
    "tailor": "Tailoring resume…",
    "applicant": "Preparing application task…",
    "tracker": "Recording result…",
}


class StreamRequest(BaseModel):
    resume_text: str = Field(min_length=50)
    keywords: list[str] = Field(default_factory=lambda: ["Python", "Backend"])


def _event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _stream_pipeline(resume_text: str):
    initial_state: AgentState = {
        "resume_text": resume_text,
        "jobs": [],
        "pipeline_status": "init",
        "errors": [],
    }

    yield _event({"type": "start", "message": "Pipeline started"})

    try:
        async for chunk in graph.astream(initial_state):
            # chunk is {node_name: state_update}
            for node_name, state_update in chunk.items():
                label = NODE_LABELS.get(node_name, node_name)
                status = state_update.get("pipeline_status", "")
                score = None
                if state_update.get("match_report"):
                    score = state_update["match_report"].get("match_score")

                yield _event({
                    "type": "node",
                    "node": node_name,
                    "label": label,
                    "pipeline_status": status,
                    "match_score": score,
                    "errors": state_update.get("errors", []),
                })

        yield _event({"type": "done", "message": "Pipeline complete"})

    except Exception as exc:
        logger.error("stream pipeline error: %s", exc)
        yield _event({"type": "error", "message": str(exc)})


@router.post("/agents/stream")
async def stream_pipeline(req: StreamRequest) -> StreamingResponse:
    """流式返回 pipeline 每个节点完成事件 (Server-Sent Events)。"""
    return StreamingResponse(
        _stream_pipeline(req.resume_text),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
