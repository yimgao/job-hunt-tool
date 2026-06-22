"""SmartRecruiters public job board API scraper.

Endpoint: https://api.smartrecruiters.com/v1/companies/{slug}/postings
Auth:     none — public job board API
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.services.scrapers.base import ScraperBase, ScrapedJob, _clean, _parse_salary
from app.services.scrapers.company_list import SMARTRECRUITERS

logger = logging.getLogger(__name__)

_BASE = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"
_DETAIL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings/{id}"
_HEADERS = {"User-Agent": "JobHunt-Flow/0.1 (personal project)"}
_CONCURRENCY = 4


class SmartRecruitersScraper(ScraperBase):
    """Pull tech jobs from SmartRecruiters job board API."""

    source_name = "smartrecruiters"

    def __init__(self, keywords: list[str], max_results: int = 40, tiers: list[str] | None = None):
        super().__init__(keywords, max_results)
        allowed = set(tiers) if tiers else {"f500", "tier1", "tier2"}
        self.companies = [(slug, name) for slug, name, tier in SMARTRECRUITERS if tier in allowed]

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

        logger.info("SmartRecruitersScraper: %d jobs from %d companies",
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
                resp = await client.get(url, params={"limit": 100, "pageSize": 100})
                if resp.status_code in (404, 401):
                    return []
                resp.raise_for_status()
            except httpx.TimeoutException:
                return []

        data = resp.json()
        postings = data.get("content", data) if isinstance(data, dict) else data
        if not isinstance(postings, list):
            postings = data.get("content", [])

        jobs: list[ScrapedJob] = []
        for item in postings:
            title = _clean(item.get("name", ""))
            location = _clean(
                (item.get("location") or {}).get("city", "") + " " +
                (item.get("location") or {}).get("country", "")
            ).strip() or "USA"
            department = _clean((item.get("department") or {}).get("label", ""))
            job_id = item.get("id", "")

            combined = (title + " " + department).lower()
            if not any(kw in combined for kw in kw_lower):
                continue

            loc_lower = location.lower()
            if not self._is_us_or_remote(loc_lower):
                continue

            ref_number = item.get("refNumber", job_id)
            apply_url = f"https://jobs.smartrecruiters.com/{slug}/{ref_number}"

            jobs.append(ScrapedJob(
                title=title[:120],
                company=company_name,
                jd_text=f"{title} at {company_name}. Department: {department}. Location: {location}.",
                source=self.source_name,
                source_id=f"sr-{job_id}",
                location=location,
                url=apply_url,
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
            "singapore", "dubai", "india", "bangalore",
        }
        has_us = any(s in location for s in us_signals)
        only_non_us = any(s in location for s in non_us_only) and not has_us
        return has_us or not only_non_us
