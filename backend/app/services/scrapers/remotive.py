"""Remotive public API scraper.

Source: https://remotive.com/api/remote-jobs
Auth:   none (public, free tier)
Docs:   https://remotive.com/api/remote-jobs?category=software-dev&search={query}

Categories: software-dev, devops-sysadmin, data, product, design, etc.
"""
from __future__ import annotations

import logging

import httpx

from app.services.scrapers.base import ScraperBase, ScrapedJob, _clean, _parse_salary

logger = logging.getLogger(__name__)

_API_URL = "https://remotive.com/api/remote-jobs"
_HEADERS = {"User-Agent": "JobHunt-Flow/0.1 (personal project)"}
_CATEGORIES = ["software-dev", "devops-sysadmin", "data"]


class RemotiveScraper(ScraperBase):
    """Fetch remote tech jobs from Remotive public API."""

    source_name = "remotive"

    async def fetch(self) -> list[ScrapedJob]:
        jobs: list[ScrapedJob] = []
        seen: set[str] = set()

        async with httpx.AsyncClient(timeout=20, headers=_HEADERS) as client:
            for category in _CATEGORIES:
                if len(jobs) >= self.max_results:
                    break
                try:
                    items = await self._fetch_category(client, category)
                    for item in items:
                        if item.source_id not in seen:
                            seen.add(item.source_id)
                            jobs.append(item)
                except Exception as exc:
                    logger.warning("RemotiveScraper category=%s error: %s", category, exc)

        logger.info("RemotiveScraper: %d jobs", len(jobs))
        return jobs[: self.max_results]

    async def _fetch_category(
        self, client: httpx.AsyncClient, category: str
    ) -> list[ScrapedJob]:
        query = " ".join(self.keywords)
        resp = await client.get(_API_URL, params={"category": category, "search": query})
        resp.raise_for_status()
        data = resp.json()

        jobs: list[ScrapedJob] = []
        kw_lower = [k.lower() for k in self.keywords]

        for item in data.get("jobs", []):
            title = _clean(item.get("title", ""))
            description = _clean(item.get("description", ""))
            company = _clean(item.get("company_name", "Unknown"))
            tags = [t.lower() for t in (item.get("tags") or [])]

            # Require keyword in title or first-party tags (Remotive tags are clean)
            combined = (title + " " + " ".join(tags)).lower()
            if not any(kw in combined for kw in kw_lower):
                continue

            sal_text = item.get("salary", "") or ""
            sal_min, sal_max = _parse_salary(sal_text + " " + description[:500])

            jobs.append(ScrapedJob(
                title=title[:120],
                company=company[:80],
                jd_text=(description or title)[:4000],
                source=self.source_name,
                source_id=str(item.get("id", title[:40])),
                location=item.get("candidate_required_location") or "Remote / Worldwide",
                url=item.get("url"),
                salary_min=sal_min,
                salary_max=sal_max,
            ))

        return jobs
