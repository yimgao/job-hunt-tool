"""Pydantic schema 验证测试。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.match import MatchDimensions, MatchReport, MatchRequest, MatchResponse


class TestMatchRequest:
    def test_valid(self):
        req = MatchRequest(resume_text="A" * 50, jd_text="B" * 50)
        assert len(req.resume_text) == 50

    def test_resume_too_short(self):
        with pytest.raises(ValidationError):
            MatchRequest(resume_text="short", jd_text="B" * 50)

    def test_jd_too_short(self):
        with pytest.raises(ValidationError):
            MatchRequest(resume_text="A" * 50, jd_text="x")


class TestMatchDimensions:
    def test_valid(self):
        d = MatchDimensions(
            skills_match=0.8,
            experience_match=0.7,
            industry_match=0.6,
            culture_fit=0.9,
        )
        assert d.skills_match == 0.8

    def test_out_of_range_high(self):
        with pytest.raises(ValidationError):
            MatchDimensions(
                skills_match=1.5, experience_match=0.5,
                industry_match=0.5, culture_fit=0.5,
            )

    def test_out_of_range_low(self):
        with pytest.raises(ValidationError):
            MatchDimensions(
                skills_match=-0.1, experience_match=0.5,
                industry_match=0.5, culture_fit=0.5,
            )


class TestMatchReport:
    def _make(self, **kwargs) -> MatchReport:
        dims = MatchDimensions(
            skills_match=0.5, experience_match=0.5,
            industry_match=0.5, culture_fit=0.5,
        )
        defaults = dict(
            job_id="job-1",
            match_score=0.7,
            confidence=0.8,
            dimensions=dims,
            strengths=["Python"],
            gaps=["Go"],
            suggestions=["Learn Go"],
            should_apply=True,
            priority="high",
        )
        defaults.update(kwargs)
        return MatchReport(**defaults)

    def test_valid(self):
        r = self._make()
        assert r.priority == "high"

    def test_invalid_priority(self):
        with pytest.raises(ValidationError):
            self._make(priority="urgent")

    def test_match_score_boundary(self):
        r = self._make(match_score=0.0)
        assert r.match_score == 0.0
        r2 = self._make(match_score=1.0)
        assert r2.match_score == 1.0

    def test_match_score_out_of_range(self):
        with pytest.raises(ValidationError):
            self._make(match_score=1.01)
