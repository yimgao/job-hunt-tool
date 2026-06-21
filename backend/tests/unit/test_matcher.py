"""MatcherService 单元测试 — 不需要真实 OpenAI key 或数据库。"""
from __future__ import annotations
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.match import MatchDimensions, MatchReport
from app.services.matcher import MatcherService


def _default_report() -> MatchReport:
    return MatchReport(
        job_id="",
        match_score=0.75,
        confidence=0.9,
        dimensions=MatchDimensions(
            skills_match=0.8, experience_match=0.7,
            industry_match=0.7, culture_fit=0.75,
        ),
        strengths=["Python", "FastAPI"],
        gaps=["Go"],
        suggestions=["Learn Go"],
        should_apply=True,
        priority="high",
    )


@pytest.fixture
def no_key_matcher():
    """MatcherService without API key — LLM calls return defaults."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OPENAI_API_KEY", None)
        return MatcherService()


@pytest.fixture
def keyed_matcher():
    """MatcherService with a fake API key."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        return MatcherService()


class TestNoLLM:
    async def test_quick_scan_returns_default(self, no_key_matcher):
        result = await no_key_matcher.quick_scan("resume text", "jd text")
        assert "match_score" in result
        assert result["match_score"] == 0.5

    async def test_deep_analyze_returns_default(self, no_key_matcher):
        report = await no_key_matcher.deep_analyze("resume text", "jd text")
        assert isinstance(report, MatchReport)
        assert report.priority == "medium"

    async def test_match_returns_tuple(self, no_key_matcher):
        report, cost = await no_key_matcher.match("A" * 200, "B" * 200)
        assert isinstance(report, MatchReport)
        assert isinstance(cost, float)
        assert cost >= 0


class TestLowScorePath:
    async def test_low_score_skips_deep_analyze(self, keyed_matcher):
        """score < 0.3 → deep_analyze should NOT be called."""
        keyed_matcher.quick_scan = AsyncMock(
            return_value={"match_score": 0.1, "confidence": 0.9, "reason": "No match"}
        )
        keyed_matcher.deep_analyze = AsyncMock()

        report, _ = await keyed_matcher.match("A" * 200, "B" * 200)

        keyed_matcher.deep_analyze.assert_not_called()
        assert report.match_score == pytest.approx(0.1)
        assert report.should_apply is False
        assert report.priority == "low"


class TestHighScorePath:
    async def test_high_score_calls_deep_analyze(self, keyed_matcher):
        """score >= 0.3 → deep_analyze should be called."""
        keyed_matcher.quick_scan = AsyncMock(
            return_value={"match_score": 0.8, "confidence": 0.9, "reason": "Good match"}
        )
        expected = _default_report()
        keyed_matcher.deep_analyze = AsyncMock(return_value=expected)

        report, _ = await keyed_matcher.match("A" * 200, "B" * 200)

        keyed_matcher.deep_analyze.assert_called_once()
        assert report.match_score == pytest.approx(0.75)
        assert report.should_apply is True
