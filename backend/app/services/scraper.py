"""ScraperService — six-source job aggregator with graceful fallback.

Sources (all public, no auth):
  1. HN "Who's Hiring"  — Algolia public API      (monthly, tech-heavy)
  2. RemoteOK           — public JSON API          (daily, remote tech)
  3. WeWorkRemotely     — RSS feed                 (daily, remote tech)
  4. Remotive           — public REST API          (daily, remote tech)
  5. Greenhouse ATS     — boards per company       (real-time, 50+ companies)
  6. Lever ATS          — postings per company     (real-time, 35+ companies)

ScraperService runs all sources concurrently; deduplicates by source_id;
falls back to mock only if every source fails.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.services.scrapers.base import ScrapedJob
from app.services.scrapers.greenhouse import GreenhouseScraper
from app.services.scrapers.hn import HNScraper
from app.services.scrapers.lever import LeverScraper
from app.services.scrapers.remoteok import RemoteOKScraper
from app.services.scrapers.remotive import RemotiveScraper
from app.services.scrapers.rss import WeWorkRemotelyScraper
from app.services.scrapers.smartrecruiters import SmartRecruitersScraper

# Re-export so callers that import ScrapeJob from this module still work
ScrapeJob = ScrapedJob

logger = logging.getLogger(__name__)


class ScraperService:
    """Aggregate jobs from all sources; dedup by source_id."""

    def __init__(
        self,
        keywords: list[str] | None = None,
        max_results: int = 80,
        tiers: list[str] | None = None,
    ):
        self.keywords = keywords or ["Python", "backend", "software engineer"]
        self.max_results = max_results
        self.tiers = tiers  # None = all tiers

    async def scrape(self) -> list[ScrapedJob]:
        scrapers = [
            HNScraper(self.keywords, max_results=30),
            RemoteOKScraper(self.keywords, max_results=20),
            WeWorkRemotelyScraper(self.keywords, max_results=20),
            RemotiveScraper(self.keywords, max_results=30),
            GreenhouseScraper(self.keywords, max_results=80, tiers=self.tiers),
            LeverScraper(self.keywords, max_results=20, tiers=self.tiers),
            SmartRecruitersScraper(self.keywords, max_results=40, tiers=self.tiers),
        ]

        # Run all scrapers concurrently
        results = await asyncio.gather(
            *[self._safe_fetch(s) for s in scrapers],
            return_exceptions=False,
        )

        # Merge + dedup by source_id
        seen_ids: set[str] = set()
        all_jobs: list[ScrapedJob] = []
        for batch in results:
            for job in batch:
                key = f"{job.source}:{job.source_id}"
                if key not in seen_ids:
                    seen_ids.add(key)
                    all_jobs.append(job)

        logger.info(
            "ScraperService: %d unique jobs from %d sources",
            len(all_jobs), len(scrapers),
        )

        if not all_jobs:
            logger.warning("ScraperService: all sources failed — mock fallback")
            return self._mock_fallback()

        return all_jobs[: self.max_results]

    @staticmethod
    async def _safe_fetch(scraper) -> list[ScrapedJob]:
        try:
            return await scraper.fetch()
        except Exception as exc:
            logger.warning(
                "ScraperService: %s failed: %s", type(scraper).__name__, exc
            )
            return []

    def _mock_fallback(self) -> list[ScrapedJob]:
        now = datetime.now(timezone.utc)
        kw = ", ".join(self.keywords)
        return [
            ScrapedJob(
                title=f"Software Engineer ({self.keywords[0]})",
                company="TechCorp (mock)",
                jd_text=(
                    f"We need a {kw} engineer. Build scalable backend systems, "
                    "PostgreSQL, Redis, Docker. Remote-friendly, USA-based team."
                ),
                source="mock",
                source_id="mock-001",
                location="Remote / USA",
                posted_at=now,
            ),
        ]
