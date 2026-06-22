"""Hacker News "Who's Hiring" scraper via Algolia public API.

Source: monthly HN thread  e.g. "Ask HN: Who is hiring? (June 2026)"
API:   https://hn.algolia.com/api/v1/search  (public, no auth)

Rate limit: 1 req/s is safe. We make 2 requests total (search + items).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import httpx

from app.services.scrapers.base import ScraperBase, ScrapedJob, _clean, _parse_salary

logger = logging.getLogger(__name__)

_ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search"
_ALGOLIA_ITEMS = "https://hn.algolia.com/api/v1/items/{id}"

# Matches the monthly hiring thread title
_HIRING_RE = re.compile(r"Ask HN: Who is hiring\?", re.IGNORECASE)
_REMOTE_TAGS = {"remote", "remote-first", "fully remote"}


def _extract_company(text: str) -> str:
    """First bold/pipe segment of the HN comment is usually 'Company | Role | Location'."""
    first_line = text.split("\n")[0].strip()
    parts = re.split(r"\s*[|/]\s*", first_line)
    if parts:
        return _clean(parts[0])[:80]
    return "Unknown"


def _extract_title(text: str) -> str:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) >= 2:
        return _clean(lines[1])[:120]
    return _clean(lines[0])[:120] if lines else "Software Engineer"


def _extract_location(text: str) -> str:
    lower = text.lower()
    if any(t in lower for t in _REMOTE_TAGS):
        return "Remote / USA"
    m = re.search(r"([A-Z][a-z]+(?:,\s*[A-Z]{2})?)", text)
    return m.group(1) if m else "USA"


class HNScraper(ScraperBase):
    """Scrape the latest 'Who's Hiring' HN thread for matching jobs."""

    source_name = "hn_hiring"

    async def fetch(self) -> list[ScrapedJob]:
        async with httpx.AsyncClient(timeout=20) as client:
            thread_id = await self._find_latest_thread(client)
            if not thread_id:
                logger.warning("HNScraper: could not find Who's Hiring thread")
                return []
            logger.info("HNScraper: found thread id=%s", thread_id)
            return await self._fetch_comments(client, thread_id)

    async def _find_latest_thread(self, client: httpx.AsyncClient) -> str | None:
        """Return the objectID of the most recent 'Who is hiring' thread."""
        params = {
            "query": "Ask HN: Who is hiring?",
            "tags": "story,ask_hn",
            "hitsPerPage": 10,
            "numericFilters": "created_at_i>1700000000",  # after Nov 2023
        }
        resp = await client.get(_ALGOLIA_SEARCH, params=params)
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits", [])
        # Sort by creation time descending to get the latest thread
        hits.sort(key=lambda h: h.get("created_at_i", 0), reverse=True)
        for hit in hits:
            if _HIRING_RE.search(hit.get("title", "")):
                return hit["objectID"]
        return None

    async def _fetch_comments(
        self, client: httpx.AsyncClient, thread_id: str
    ) -> list[ScrapedJob]:
        resp = await client.get(_ALGOLIA_ITEMS.format(id=thread_id))
        resp.raise_for_status()
        data = resp.json()
        children = data.get("children", [])

        jobs: list[ScrapedJob] = []
        kw_lower = [k.lower() for k in self.keywords]

        for comment in children:
            text = _clean(comment.get("text", ""))
            if not text or len(text) < 50:
                continue

            text_lower = text.lower()
            if not any(kw in text_lower for kw in kw_lower):
                continue

            # filter: must mention USA/remote/US or no geo restriction
            if not self._is_us_job(text_lower):
                continue

            company = _extract_company(text)
            title = _extract_title(text)
            location = _extract_location(text)
            sal_min, sal_max = _parse_salary(text)

            job = ScrapedJob(
                title=title or "Software Engineer",
                company=company or "Unknown",
                jd_text=text[:4000],
                source=self.source_name,
                source_id=str(comment.get("id", "")),
                location=location,
                url=f"https://news.ycombinator.com/item?id={comment.get('id', '')}",
                salary_min=sal_min,
                salary_max=sal_max,
                posted_at=datetime.fromtimestamp(
                    comment.get("created_at_i", 0), tz=timezone.utc
                ) if comment.get("created_at_i") else datetime.now(timezone.utc),
            )
            jobs.append(job)

            if len(jobs) >= self.max_results:
                break

        logger.info("HNScraper: extracted %d matching jobs", len(jobs))
        return jobs

    @staticmethod
    def _is_us_job(text_lower: str) -> bool:
        """Return True if the job is US-based or remote-friendly (not EU/Asia-only)."""
        # Hard exclusions first
        exclusions = {
            "eu only", "europe only", "ireland only", "uk only", "germany only",
            "onsite in london", "onsite in berlin", "onsite in amsterdam",
            "no us", "not us", "non-us", "outside us",
        }
        if any(excl in text_lower for excl in exclusions):
            return False

        us_signals = {
            "remote", "worldwide", "global", "usa", "united states", "u.s.",
            "san francisco", "new york", "seattle", "austin", "boston",
            "chicago", "los angeles", "sf", "nyc", "la", "dc", "washington",
            "new grad", "entry level",
        }
        return any(s in text_lower for s in us_signals)
