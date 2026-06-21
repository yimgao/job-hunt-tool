"""Matcher 服务 — Gemini free tier 初筛 → GPT-4o-mini 深度分析。

LLM 路由策略 (COST.md):
  quick_scan  → Gemini 1.5 Flash (free tier, 60 req/min)
              → fallback: GPT-4o-mini
  deep_analyze→ GPT-4o-mini (Structured Outputs)

Phase 4: 接入真实 RAG 召回（VectorStore.search）。
Phase 1 降级: 无 API key → 返回默认分数。
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from openai import AsyncOpenAI

from app.schemas.match import MatchDimensions, MatchReport
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)


class MatcherService:
    """JD-简历匹配服务。"""

    def __init__(self, vector_store=None):
        openai_key = os.getenv("OPENAI_API_KEY", "")
        self.client = AsyncOpenAI(api_key=openai_key) if openai_key else None
        self.vector_store = vector_store
        self.llm_model = os.getenv("LLM_MATCHER_MODEL", "gpt-4o-mini")

        # Gemini via OpenAI-compatible endpoint (no extra SDK needed)
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_client = (
            AsyncOpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            if gemini_key
            else None
        )
        self.gemini_model = os.getenv("GEMINI_QUICK_SCAN_MODEL", "gemini-1.5-flash")

    # ── Quick scan (Gemini free tier → GPT-4o-mini fallback) ─────────────────

    @with_retry(max_retries=2, base_delay=1.0)
    async def quick_scan(
        self, resume_snippet: str, jd_text: str
    ) -> dict[str, Any]:
        """低成本初筛 — 优先 Gemini 1.5 Flash（免费），失败后回退 GPT-4o-mini。"""
        prompt = f"""你是一个招聘匹配助手。快速判断候选人是否适合该职位。

候选人经历片段:
{resume_snippet[:1500]}

职位描述:
{jd_text[:1500]}

只输出 JSON，不要其他内容:
{{"match_score": 0.0-1.0, "confidence": 0.0-1.0, "reason": "一句话理由"}}
"""
        # 优先 Gemini free tier
        for client, model, label in [
            (self.gemini_client, self.gemini_model, "Gemini"),
            (self.client, "gpt-4o-mini", "GPT-4o-mini"),
        ]:
            if not client:
                continue
            try:
                resp = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                )
                content = resp.choices[0].message.content or "{}"
                result = json.loads(content)
                logger.debug("quick_scan via %s: score=%.2f", label, result.get("match_score", 0))
                return result
            except Exception as exc:
                logger.warning("quick_scan %s failed: %s", label, exc)

        return {"match_score": 0.5, "confidence": 0.5, "reason": "No LLM configured"}

    # ── Deep analyze (GPT-4o-mini Structured Outputs) ────────────────────────

    @with_retry(max_retries=2, base_delay=2.0)
    async def deep_analyze(self, resume_text: str, jd_text: str) -> MatchReport:
        """深度匹配分析 — Structured Outputs，强制输出 MatchReport schema。"""
        if not self.client:
            return self._default_report(0.5)

        prompt = f"""你叫「鉴宝师」，资深招聘顾问。输出详细的匹配报告。

候选人简历:
{resume_text[:3000]}

职位描述:
{jd_text[:3000]}

评估维度:
1. 技能匹配 — 硬技能重合度
2. 经验匹配 — 行业/岗位年限匹配度
3. 项目匹配 — 项目复杂度、规模
4. 潜力匹配 — 学习能力、转型可行性"""

        resp = await self.client.beta.chat.completions.parse(
            model=self.llm_model,
            messages=[{"role": "user", "content": prompt}],
            response_format=MatchReport,
            temperature=0.3,
        )
        report = resp.choices[0].message.parsed
        if not isinstance(report, MatchReport):
            raise ValueError("LLM did not return a valid MatchReport")
        return report

    # ── Main entry point ──────────────────────────────────────────────────────

    async def match(
        self, resume_text: str, jd_text: str
    ) -> tuple[MatchReport, float]:
        """完整匹配流程。Returns (MatchReport, cost_estimate_usd)."""
        start = time.time()

        # 1. RAG 召回（Phase 4: 若有 VectorStore + user_id 则真实召回）
        chunks: list[str] = []
        if self.vector_store:
            try:
                raw = await self.vector_store.chunk_resume(resume_text)
                chunks = raw
            except Exception as exc:
                logger.warning("vector_store.chunk_resume failed: %s", exc)

        snippet = chunks[0][:2000] if chunks else resume_text[:2000]

        # 2. 初筛
        quick = await self.quick_scan(snippet, jd_text[:2000])
        score = float(quick.get("match_score", 0))

        # 3. 低分 → 直接返回
        if score < 0.3:
            elapsed = time.time() - start
            return self._default_report(score, quick), 0.0001 * elapsed

        # 4. 高分 → 深度分析
        try:
            report = await self.deep_analyze(resume_text, jd_text)
        except Exception as exc:
            logger.error("deep_analyze failed, using quick_scan score: %s", exc)
            report = self._default_report(score, quick)

        elapsed = time.time() - start
        cost = 0.0002 * elapsed
        return report, cost

    def _default_report(
        self, score: float, quick: dict[str, Any] | None = None
    ) -> MatchReport:
        quick = quick or {}
        priority = "high" if score >= 0.6 else "medium" if score >= 0.3 else "low"
        return MatchReport(
            job_id="",
            match_score=score,
            confidence=float(quick.get("confidence", 0.5)),
            dimensions=MatchDimensions(
                skills_match=score,
                experience_match=score,
                industry_match=score,
                culture_fit=score,
            ),
            strengths=[],
            gaps=[],
            suggestions=[quick.get("reason", "No LLM configured — using default score")],
            should_apply=score >= 0.6,
            priority=priority,
        )
