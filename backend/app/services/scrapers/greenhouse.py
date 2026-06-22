"""Greenhouse ATS public API scraper.

Endpoint: https://boards.greenhouse.io/api/v1/boards/{company}/jobs?content=true
Auth:     none — fully public
Docs:     https://developers.greenhouse.io/job-board.html#list-jobs

Fetches jobs from curated company list concurrently (semaphore=6).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.services.scrapers.base import ScraperBase, ScrapedJob, _clean, _parse_salary
from app.services.scrapers.company_list import GREENHOUSE

logger = logging.getLogger(__name__)

_BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
_HEADERS = {"User-Agent": "JobHunt-Flow/0.1 (personal project)"}
_CONCURRENCY = 6  # polite parallel limit


class GreenhouseScraper(ScraperBase):
    """Pull tech jobs from Greenhouse ATS across curated company list."""

    source_name = "greenhouse"

    def __init__(
        self,
        keywords: list[str],
        max_results: int = 60,
        tiers: list[str] | None = None,
    ):
        super().__init__(keywords, max_results)
        # Filter company list by tier if specified
        allowed = set(tiers) if tiers else {"f500", "tier1", "tier2"}
        self.companies = [(slug, name) for slug, name, tier in GREENHOUSE if tier in allowed]

    async def fetch(self) -> list[ScrapedJob]:
        sem = asyncio.Semaphore(_CONCURRENCY)
        kw_lower = [k.lower() for k in self.keywords]
        jobs: list[ScrapedJob] = []

        async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
            tasks = [self._fetch_company(client, sem, slug, name, kw_lower)
                     for slug, name in self.companies]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                jobs.extend(result)
            elif isinstance(result, Exception):
                logger.debug("GreenhouseScraper company error (skipped): %s", result)

        logger.info("GreenhouseScraper: %d matching jobs from %d companies",
                    len(jobs), len(self.companies))
        return jobs[: self.max_results]

    async def _fetch_company(
        self,
        client: httpx.AsyncClient,
        sem: asyncio.Semaphore,
        slug: str,
        company_name: str,
        kw_lower: list[str],
    ) -> list[ScrapedJob]:
        url = _BASE.format(slug=slug)
        async with sem:
            try:
                resp = await client.get(url, params={"content": "true"})
                if resp.status_code == 404:
                    return []  # company migrated ATS — skip silently
                resp.raise_for_status()
            except httpx.TimeoutException:
                logger.debug("GreenhouseScraper: timeout for %s", slug)
                return []

        data = resp.json()
        jobs: list[ScrapedJob] = []

        for item in data.get("jobs", []):
            title = _clean(item.get("title", ""))
            content = _clean(item.get("content", ""))
            location = _clean(
                (item.get("location") or {}).get("name", "USA")
            )
            url_apply = item.get("absolute_url", "")

            # Keyword filter: title + content
            combined = (title + " " + content[:1000]).lower()
            if not any(kw in combined for kw in kw_lower):
                continue

            # US/Remote filter: skip obvious non-US onsite postings
            loc_lower = location.lower()
            if loc_lower and not self._is_us_or_remote(loc_lower):
                continue

            sal_min, sal_max = _parse_salary(content[:1000])
            updated_at = item.get("updated_at", "")
            try:
                posted_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                posted_at = datetime.now(timezone.utc)

            jobs.append(ScrapedJob(
                title=title[:120],
                company=company_name,
                jd_text=(content or title)[:4000],
                source=self.source_name,
                source_id=f"gh-{item.get('id', '')}",
                location=location or "USA",
                url=url_apply or None,
                salary_min=sal_min,
                salary_max=sal_max,
                posted_at=posted_at,
            ))

        return jobs

    @staticmethod
    def _is_us_or_remote(location: str) -> bool:
        us_signals = {
            "remote", "usa", "united states", "u.s.", "new york", "san francisco",
            "seattle", "austin", "boston", "chicago", "los angeles", "sf", "nyc",
            "washington", "atlanta", "denver", "miami", "worldwide", "global",
        }
        non_us_only = {
            "london", "berlin", "amsterdam", "paris", "toronto", "sydney",
            "singapore", "dubai", "india", "bangalore", "mexico",
        }
        has_us = any(s in location for s in us_signals)
        only_non_us = any(s in location for s in non_us_only) and not has_us
        return has_us or not only_non_us
