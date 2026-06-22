"""RemoteOK public JSON API scraper.

Source: https://remoteok.com/api
Auth:   none (public, free)
Limit:  be polite — 1 req per run, cache TTL 1h recommended
"""
from __future__ import annotations

import logging

import httpx

from app.services.scrapers.base import ScraperBase, ScrapedJob, _clean, _parse_salary

logger = logging.getLogger(__name__)

_API_URL = "https://remoteok.com/api"
_HEADERS = {
    # RemoteOK asks for a descriptive User-Agent
    "User-Agent": "JobHunt-Flow/0.1 (job-hunt-tool; personal project)",
    "Accept": "application/json",
}


class RemoteOKScraper(ScraperBase):
    """Fetch remote US-friendly jobs from RemoteOK public API."""

    source_name = "remoteok"

    async def fetch(self) -> list[ScrapedJob]:
        async with httpx.AsyncClient(timeout=30, headers=_HEADERS) as client:
            resp = await client.get(_API_URL)
            resp.raise_for_status()
            raw = resp.json()

        # First element is a meta/legal notice dict — skip it
        listings = [r for r in raw if isinstance(r, dict) and r.get("id")]
        kw_lower = [k.lower() for k in self.keywords]
        jobs: list[ScrapedJob] = []

        for item in listings:
            tags = [t.lower() for t in (item.get("tags") or [])]
            title = _clean(item.get("position", ""))
            description = _clean(item.get("description", ""))

            # RemoteOK appends 50+ site-wide catch-all tags to every listing.
            # Only the first ~8 tags are job-specific; use title + first 8 tags.
            specific_tags = tags[:8]
            title_and_tags = (title + " " + " ".join(specific_tags)).lower()
            if not any(kw in title_and_tags for kw in kw_lower):
                continue

            company = _clean(item.get("company", "Unknown"))
            location = item.get("location") or "Remote / Worldwide"

            sal_text = f"{item.get('salary_min', '')} {item.get('salary_max', '')}"
            sal_min = item.get("salary_min")
            sal_max = item.get("salary_max")
            if not sal_min:
                sal_min, sal_max = _parse_salary(description)

            url = item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"

            jd_text = description or f"{title} at {company}. Tags: {', '.join(tags)}."

            jobs.append(ScrapedJob(
                title=title or "Remote Engineer",
                company=company,
                jd_text=jd_text[:4000],
                source=self.source_name,
                source_id=str(item["id"]),
                location=location,
                url=url,
                salary_min=int(sal_min) if sal_min else None,
                salary_max=int(sal_max) if sal_max else None,
            ))

            if len(jobs) >= self.max_results:
                break

        logger.info("RemoteOKScraper: extracted %d matching jobs", len(jobs))
        return jobs
