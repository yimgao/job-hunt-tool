"""ScraperService — multi-source job scraper with three-tier fallback.

Tier 1 (fastest, free):
  - HN "Who's Hiring" — Algolia public API
  - RemoteOK          — public JSON API
  - Indeed RSS        — public RSS feed

Tier 2 / Tier 3: reserved for paid APIs and HTML scraping.

All real scrapers live in app/services/scrapers/.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.services.scrapers.base import ScrapedJob
from app.services.scrapers.hn import HNScraper
from app.services.scrapers.remoteok import RemoteOKScraper
from app.services.scrapers.rss import WeWorkRemotelyScraper

# Re-export for callers that import ScrapeJob from this module
ScrapeJob = ScrapedJob

logger = logging.getLogger(__name__)


class ScraperService:
    """Run all Tier-1 scrapers in sequence; deduplicate by source_id."""

    def __init__(self, keywords: list[str] | None = None, max_results: int = 50):
        self.keywords = keywords or ["Python", "Backend", "FastAPI"]
        self.max_results = max_results

    async def scrape(self) -> list[ScrapedJob]:
        """Aggregate jobs from all sources, dedup by source_id."""
        all_jobs: list[ScrapedJob] = []
        seen_ids: set[str] = set()

        scrapers = [
            HNScraper(self.keywords, max_results=self.max_results),
            RemoteOKScraper(self.keywords, max_results=self.max_results),
            WeWorkRemotelyScraper(self.keywords, max_results=20),
        ]

        for scraper in scrapers:
            try:
                jobs = await scraper.fetch()
                for job in jobs:
                    key = f"{scraper.source_name}:{job.source_id}"
                    if key not in seen_ids:
                        seen_ids.add(key)
                        all_jobs.append(job)
            except Exception as exc:
                logger.warning("ScraperService: %s failed: %s", type(scraper).__name__, exc)

        logger.info("ScraperService: total %d unique jobs from %d sources", len(all_jobs), len(scrapers))

        if not all_jobs:
            logger.warning("ScraperService: all scrapers failed — returning mock fallback")
            return self._mock_fallback()

        return all_jobs[: self.max_results]

    def _mock_fallback(self) -> list[ScrapedJob]:
        """Last-resort fallback so the pipeline never returns empty-handed."""
        now = datetime.now(timezone.utc)
        kw = ", ".join(self.keywords)
        return [
            ScrapedJob(
                title=f"Senior {self.keywords[0]} Engineer",
                company="TechCorp (mock)",
                jd_text=(
                    f"We need a Senior {kw} engineer with 3+ years of experience. "
                    "Build scalable backend systems, PostgreSQL, Redis, Docker. "
                    "Remote-friendly, USA-based team."
                ),
                source="mock",
                source_id="mock-001",
                location="Remote / USA",
                url=None,
                posted_at=now,
            ),
        ]
