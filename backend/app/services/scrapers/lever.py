"""Lever ATS public API scraper.

Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
Auth:     none — fully public
Docs:     https://hire.lever.co/developer/postings

Fetches jobs from curated company list concurrently (semaphore=6).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.services.scrapers.base import ScraperBase, ScrapedJob, _clean, _parse_salary
from app.services.scrapers.company_list import LEVER

logger = logging.getLogger(__name__)

_BASE = "https://api.lever.co/v0/postings/{slug}"
_HEADERS = {"User-Agent": "JobHunt-Flow/0.1 (personal project)"}
_CONCURRENCY = 6


class LeverScraper(ScraperBase):
    """Pull tech jobs from Lever ATS across curated company list."""

    source_name = "lever"

    def __init__(
        self,
        keywords: list[str],
        max_results: int = 60,
        tiers: list[str] | None = None,
    ):
        super().__init__(keywords, max_results)
        allowed = set(tiers) if tiers else {"f500", "tier1", "tier2"}
        self.companies = [(slug, name) for slug, name, tier in LEVER if tier in allowed]

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
                logger.debug("LeverScraper company error (skipped): %s", result)

        logger.info("LeverScraper: %d matching jobs from %d companies",
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
                resp = await client.get(url, params={"mode": "json"})
                if resp.status_code in (404, 410):
                    return []
                resp.raise_for_status()
            except httpx.TimeoutException:
                logger.debug("LeverScraper: timeout for %s", slug)
                return []

        postings = resp.json()
        if not isinstance(postings, list):
            return []

        jobs: list[ScrapedJob] = []

        for item in postings:
            title = _clean(item.get("text", ""))
            team = _clean((item.get("categories") or {}).get("team", ""))
            location = _clean((item.get("categories") or {}).get("location", "USA"))
            commitment = _clean((item.get("categories") or {}).get("commitment", ""))

            # Build JD text from Lever's lists object
            lists = item.get("lists") or []
            description_parts = [title, team]
            for lst in lists:
                description_parts.append(_clean(lst.get("text", "")))
                description_parts.append(_clean(lst.get("content", "")))
            additional = _clean((item.get("additional") or ""))
            description_parts.append(additional)
            jd_text = " ".join(p for p in description_parts if p)[:4000]

            # Keyword filter
            combined = (title + " " + team + " " + jd_text[:800]).lower()
            if not any(kw in combined for kw in kw_lower):
                continue

            # US/Remote filter
            loc_lower = location.lower()
            if loc_lower and not self._is_us_or_remote(loc_lower):
                continue

            sal_min, sal_max = _parse_salary(jd_text[:500])
            created_at = item.get("createdAt", 0)
            posted_at = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc) \
                if created_at else datetime.now(timezone.utc)

            jobs.append(ScrapedJob(
                title=title[:120],
                company=company_name,
                jd_text=jd_text or title,
                source=self.source_name,
                source_id=f"lv-{item.get('id', '')}",
                location=location or "USA",
                url=item.get("hostedUrl") or item.get("applyUrl"),
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
