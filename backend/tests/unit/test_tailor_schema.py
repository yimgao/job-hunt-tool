"""TailorOutput schema 验证测试。"""
from __future__ import annotations

from pydantic import ValidationError
import pytest

from app.schemas.tailor import TailorOutput


class TestTailorOutput:
    def test_valid(self):
        out = TailorOutput(
            tailored_resume="resume text here",
            cover_letter="dear hiring manager...",
            key_changes=["added FastAPI to skills"],
            match_keywords=["FastAPI", "Python"],
        )
        assert out.tailored_resume == "resume text here"

    def test_empty_lists_allowed(self):
        out = TailorOutput(
            tailored_resume="resume",
            cover_letter="letter",
            key_changes=[],
            match_keywords=[],
        )
        assert out.key_changes == []

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            TailorOutput(tailored_resume="resume", cover_letter="letter")
