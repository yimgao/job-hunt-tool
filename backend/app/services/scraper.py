"""三重降级爬虫服务。

降级策略:
  Tier 1: RSS / 轻量 API (免费，无需认证)
  Tier 2: 平台搜索 API (需 key，按量计费)
  Tier 3: HTTP 爬取 + 简单解析 (最后兜底)

Phase 2 实现: Tier 1 返回模拟数据，Tier 2/3 为结构性占位。
Phase 3+: 接入真实爬虫 (httpx + BeautifulSoup)。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScrapeJob:
    """爬取到的单条职位数据（未入库）。"""
    title: str
    company: str
    jd_text: str
    source: str
    source_id: str | None = None
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    url: str | None = None
    posted_at: datetime | None = None
    skills: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "company": self.company,
            "jd_text": self.jd_text,
            "source": self.source,
            "source_id": self.source_id,
            "location": self.location,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "url": self.url,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "skills": self.skills,
        }


class ScraperService:
    """三重降级爬虫 — 按优先级尝试，失败自动降级。"""

    def __init__(self, keywords: list[str] | None = None, max_results: int = 50):
        self.keywords = keywords or ["Python", "Backend", "FastAPI"]
        self.max_results = max_results

    async def scrape(self) -> list[ScrapeJob]:
        """按降级顺序尝试爬取，返回职位列表。"""
        for tier_fn, tier_name in [
            (self._tier1_rss, "RSS"),
            (self._tier2_api, "API"),
            (self._tier3_http, "HTTP"),
        ]:
            try:
                results = await tier_fn()
                if results:
                    logger.info("Scraper: %s tier returned %d jobs", tier_name, len(results))
                    return results[: self.max_results]
            except Exception as exc:
                logger.warning("Scraper: %s tier failed: %s", tier_name, exc)

        logger.error("Scraper: all tiers failed, returning empty list")
        return []

    async def _tier1_rss(self) -> list[ScrapeJob]:
        """Tier 1: RSS / 免费 API。Phase 2 使用模拟数据。"""
        now = datetime.now(timezone.utc)
        kw = ", ".join(self.keywords)
        return [
            ScrapeJob(
                title=f"Senior {self.keywords[0]} Engineer",
                company="TechCorp",
                jd_text=(
                    f"We are looking for a Senior {kw} engineer with 5+ years of experience. "
                    "You will design and build scalable backend systems, "
                    "collaborate with cross-functional teams, and mentor junior engineers. "
                    "Requirements: strong proficiency in Python, experience with FastAPI or Django, "
                    "PostgreSQL, Redis, Docker, Kubernetes. Nice to have: LLM/AI experience."
                ),
                source="rss_mock",
                source_id="rss-mock-001",
                location="Remote",
                salary_min=200000,
                salary_max=300000,
                url="https://example.com/jobs/001",
                posted_at=now,
            ),
            ScrapeJob(
                title=f"Backend {self.keywords[0]} Developer",
                company="StartupXYZ",
                jd_text=(
                    f"Seeking a Backend Developer skilled in {kw}. "
                    "Join our fast-growing team to build the next-generation platform. "
                    "Tech stack: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL, pgvector, AWS. "
                    "Must have 3+ years backend experience and enthusiasm for AI/ML products."
                ),
                source="rss_mock",
                source_id="rss-mock-002",
                location="San Francisco, CA",
                salary_min=180000,
                salary_max=250000,
                url="https://example.com/jobs/002",
                posted_at=now,
            ),
        ]

    async def _tier2_api(self) -> list[ScrapeJob]:
        """Tier 2: 平台搜索 API（需 API key）。Phase 3 实现。"""
        raise NotImplementedError("Tier 2 API scraper not yet implemented")

    async def _tier3_http(self) -> list[ScrapeJob]:
        """Tier 3: HTTP 爬取 + HTML 解析。Phase 3 实现。"""
        raise NotImplementedError("Tier 3 HTTP scraper not yet implemented")
