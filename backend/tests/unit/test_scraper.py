"""ScraperService 单元测试。"""
from __future__ import annotations

import pytest

from app.services.scraper import ScraperService


class TestScraperService:
    async def test_scrape_returns_list(self):
        service = ScraperService(keywords=["Python"])
        results = await service.scrape()
        assert isinstance(results, list)

    async def test_scrape_returns_scrape_jobs(self):
        service = ScraperService(keywords=["Python"])
        results = await service.scrape()
        assert len(results) > 0
        for job in results:
            assert job.title
            assert job.company
            assert len(job.jd_text) > 50

    async def test_respects_max_results(self):
        service = ScraperService(keywords=["Python"], max_results=1)
        results = await service.scrape()
        assert len(results) <= 1

    async def test_to_dict_has_required_keys(self):
        service = ScraperService()
        results = await service.scrape()
        assert results
        d = results[0].to_dict()
        for key in ("title", "company", "jd_text", "source"):
            assert key in d
