"""Generic RSS/Atom feed scraper.

Supports:
  - Indeed RSS  (public, no auth)
  - We Work Remotely RSS (public)
  - Any Atom/RSS 2.0 feed

Indeed RSS format:
  https://www.indeed.com/rss?q={query}&l={location}&sort=date&limit=25
"""
from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode

import httpx

from app.services.scrapers.base import ScraperBase, ScrapedJob, _clean, _parse_salary

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "JobHunt-Flow/0.1 (job-hunt-tool; personal project)",
    "Accept": "application/rss+xml, application/xml, text/xml",
}

# Namespaces used by some feeds
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
}


def _build_indeed_url(query: str, location: str = "United States") -> str:
    params = urlencode({"q": query, "l": location, "sort": "date", "limit": "25"})
    return f"https://www.indeed.com/rss?{params}"


def _parse_rfc822(date_str: str | None) -> datetime:
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return datetime.now(timezone.utc)


def _extract_items(root: ET.Element) -> list[ET.Element]:
    """Handle both RSS 2.0 <item> and Atom <entry>."""
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//atom:entry", _NS)
    return items


def _text(elem: ET.Element, tag: str, ns: str = "") -> str:
    key = f"{ns}{tag}" if ns else tag
    child = elem.find(key)
    if child is None:
        return ""
    return _clean(html.unescape(child.text or ""))


class IndeedRSSScraper(ScraperBase):
    """Pull jobs from Indeed's public RSS feed.

    No auth required. Indeed RSS is publicly documented and widely used by
    job aggregators (including jobright.ai itself).
    """

    source_name = "indeed_rss"

    def __init__(
        self,
        keywords: list[str],
        location: str = "United States",
        max_results: int = 30,
    ):
        super().__init__(keywords, max_results)
        self.location = location

    async def fetch(self) -> list[ScrapedJob]:
        query = " ".join(self.keywords)
        url = _build_indeed_url(query, self.location)
        logger.info("IndeedRSSScraper: fetching %s", url)

        async with httpx.AsyncClient(timeout=20, headers=_HEADERS, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        root = ET.fromstring(resp.content)
        items = _extract_items(root)
        jobs: list[ScrapedJob] = []

        for item in items:
            title = _text(item, "title")
            link = _text(item, "link") or _text(item, "guid")
            description = _text(item, "description")
            pub_date = _text(item, "pubDate")
            company_loc = _text(item, "source") or ""

            # Indeed puts "Job Title - Company - Location" in title
            parts = [p.strip() for p in title.split(" - ")]
            job_title = parts[0] if parts else title
            company = parts[1] if len(parts) > 1 else "Unknown"
            location = parts[2] if len(parts) > 2 else self.location

            jd_text = description or job_title
            if len(jd_text) < 30:
                jd_text = f"{job_title} at {company}. Location: {location}."

            sal_min, sal_max = _parse_salary(jd_text)
            source_id = re.sub(r"[^a-zA-Z0-9]", "", link)[-40:] if link else title[:40]

            jobs.append(ScrapedJob(
                title=job_title[:120],
                company=company[:80],
                jd_text=jd_text[:4000],
                source=self.source_name,
                source_id=source_id,
                location=location,
                url=link or None,
                salary_min=sal_min,
                salary_max=sal_max,
                posted_at=_parse_rfc822(pub_date),
            ))

            if len(jobs) >= self.max_results:
                break

        logger.info("IndeedRSSScraper: extracted %d jobs", len(jobs))
        return jobs


class WeWorkRemotelyScraper(ScraperBase):
    """Pull jobs from We Work Remotely RSS feed.

    Source: https://weworkremotely.com/categories/remote-programming-jobs.rss
    Auth:   none
    """

    source_name = "weworkremotely"
    _RSS_URL = "https://weworkremotely.com/categories/remote-programming-jobs.rss"

    async def fetch(self) -> list[ScrapedJob]:
        logger.info("WeWorkRemotelyScraper: fetching RSS")
        async with httpx.AsyncClient(timeout=20, headers=_HEADERS, follow_redirects=True) as client:
            resp = await client.get(self._RSS_URL)
            resp.raise_for_status()

        root = ET.fromstring(resp.content)
        items = _extract_items(root)
        kw_lower = [k.lower() for k in self.keywords]
        jobs: list[ScrapedJob] = []

        for item in items:
            title = _text(item, "title")
            description = _text(item, "description")
            link = _text(item, "link") or _text(item, "guid")
            pub_date = _text(item, "pubDate")

            combined = (title + " " + description).lower()
            if not any(kw in combined for kw in kw_lower):
                continue

            # WWR title format: "Company: Job Title"
            if ": " in title:
                company, job_title = title.split(": ", 1)
            else:
                company, job_title = "Unknown", title

            sal_min, sal_max = _parse_salary(description)
            source_id = re.sub(r"[^a-zA-Z0-9]", "", link)[-40:] if link else title[:40]

            jobs.append(ScrapedJob(
                title=job_title[:120],
                company=company[:80],
                jd_text=(description or job_title)[:4000],
                source=self.source_name,
                source_id=source_id,
                location="Remote / Worldwide",
                url=link or None,
                salary_min=sal_min,
                salary_max=sal_max,
                posted_at=_parse_rfc822(pub_date),
            ))

            if len(jobs) >= self.max_results:
                break

        logger.info("WeWorkRemotelyScraper: extracted %d matching jobs", len(jobs))
        return jobs
