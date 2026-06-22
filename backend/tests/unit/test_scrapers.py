"""Tests for multi-source scrapers — mocks HTTP to avoid real network calls."""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.scrapers.base import ScrapedJob, _clean, _parse_salary, is_entry_level
from app.services.scrapers.hn import HNScraper
from app.services.scrapers.remoteok import RemoteOKScraper
from app.services.scrapers.rss import IndeedRSSScraper, WeWorkRemotelyScraper


# ── base helpers ────────────────────────────────────────────────────────────

def test_clean_strips_html():
    assert _clean("<p>Hello <b>world</b></p>") == "Hello world"


def test_clean_handles_none():
    assert _clean(None) == ""


def test_parse_salary_range():
    lo, hi = _parse_salary("$120k - $160k per year")
    assert lo == 120_000
    assert hi == 160_000


def test_parse_salary_single():
    lo, hi = _parse_salary("Compensation: 90k")
    assert lo == 90_000
    assert hi is None


def test_parse_salary_none():
    lo, hi = _parse_salary("Competitive salary")
    assert lo is None and hi is None


def test_is_entry_level_positive():
    assert is_entry_level("Junior Python Developer", "")
    assert is_entry_level("Entry Level Engineer", "")
    assert is_entry_level("Engineer", "New grad position, 0-1 year experience")


def test_is_entry_level_negative():
    assert not is_entry_level("Senior Backend Engineer", "5+ years required")


def test_scraped_job_content_hash_stable():
    job = ScrapedJob(
        title="Backend Engineer", company="Acme",
        jd_text="We build distributed systems.", source="test", source_id="1"
    )
    h1 = job.content_hash
    h2 = job.content_hash
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_scraped_job_to_dict():
    job = ScrapedJob(
        title="SWE", company="Co", jd_text="Build stuff", source="hn", source_id="42"
    )
    d = job.to_dict()
    assert d["title"] == "SWE"
    assert "content_hash" in d
    assert d["source"] == "hn"


# ── HN scraper ──────────────────────────────────────────────────────────────

_HN_SEARCH_RESPONSE = {
    "hits": [{"objectID": "99999", "title": "Ask HN: Who is hiring? (June 2026)"}]
}

_HN_ITEMS_RESPONSE = {
    "children": [
        {
            "id": 100001,
            "created_at_i": 1700000000,
            "text": (
                "Acme Corp | Senior Python Engineer | Remote / USA\n"
                "We are looking for a Python backend engineer. FastAPI, PostgreSQL, Redis. "
                "Fully remote, US timezone. $150k-$200k. Apply at acme.com/jobs."
            ),
        },
        {
            "id": 100002,
            "created_at_i": 1700000001,
            "text": (
                "Berlin Startup | Go Developer | ONSITE Berlin Germany\n"
                "No US presence. Must be in Berlin."
            ),
        },
        {"id": 100003, "created_at_i": 0, "text": "short"},  # should be filtered
    ]
}


@pytest.mark.asyncio
async def test_hn_scraper_extracts_us_jobs():
    scraper = HNScraper(keywords=["Python", "FastAPI"], max_results=10)

    mock_client = AsyncMock()
    search_resp = MagicMock()
    search_resp.raise_for_status = MagicMock()
    search_resp.json.return_value = _HN_SEARCH_RESPONSE

    items_resp = MagicMock()
    items_resp.raise_for_status = MagicMock()
    items_resp.json.return_value = _HN_ITEMS_RESPONSE

    mock_client.get = AsyncMock(side_effect=[search_resp, items_resp])

    with patch("app.services.scrapers.hn.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        jobs = await scraper.fetch()

    assert len(jobs) == 1
    assert "Acme" in jobs[0].company
    assert jobs[0].source == "hn_hiring"
    assert jobs[0].salary_min == 150_000


@pytest.mark.asyncio
async def test_hn_scraper_returns_empty_when_thread_not_found():
    scraper = HNScraper(keywords=["Python"], max_results=10)
    mock_client = AsyncMock()
    search_resp = MagicMock()
    search_resp.raise_for_status = MagicMock()
    search_resp.json.return_value = {"hits": []}
    mock_client.get = AsyncMock(return_value=search_resp)

    with patch("app.services.scrapers.hn.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        jobs = await scraper.fetch()

    assert jobs == []


# ── RemoteOK scraper ────────────────────────────────────────────────────────

_REMOTEOK_RESPONSE = [
    {"legal": "Please don't abuse the API"},  # meta, should be skipped
    {
        "id": "remoteok-123",
        "position": "Python Backend Engineer",
        "company": "Remote Startup",
        "description": "Build APIs with Python and FastAPI. Remote friendly. $120k-$150k.",
        "tags": ["python", "fastapi", "postgresql"],
        "location": "Worldwide",
        "url": "https://remoteok.com/remote-jobs/remoteok-123",
        "salary_min": 120000,
        "salary_max": 150000,
    },
    {
        "id": "remoteok-456",
        "position": "iOS Developer",
        "company": "App Co",
        "description": "Build iOS apps with Swift.",
        "tags": ["ios", "swift"],
        "location": "Remote",
        "url": "https://remoteok.com/remote-jobs/remoteok-456",
    },
]


@pytest.mark.asyncio
async def test_remoteok_filters_by_keyword():
    scraper = RemoteOKScraper(keywords=["Python", "FastAPI"], max_results=10)
    mock_client = AsyncMock()
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = _REMOTEOK_RESPONSE
    mock_client.get = AsyncMock(return_value=resp)

    with patch("app.services.scrapers.remoteok.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        jobs = await scraper.fetch()

    assert len(jobs) == 1
    assert jobs[0].company == "Remote Startup"
    assert jobs[0].salary_min == 120_000
    assert jobs[0].source == "remoteok"


# ── Indeed RSS scraper ───────────────────────────────────────────────────────

_INDEED_RSS = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Indeed Jobs</title>
    <item>
      <title>Python Developer - Acme Inc - Remote</title>
      <link>https://www.indeed.com/viewjob?jk=abc123</link>
      <description>Python FastAPI developer needed. $100k-$130k. Remote, USA.</description>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Java Developer - Corp - New York</title>
      <link>https://www.indeed.com/viewjob?jk=def456</link>
      <description>Java Spring developer for NYC office.</description>
      <pubDate>Mon, 01 Jan 2026 00:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


@pytest.mark.asyncio
async def test_indeed_rss_parses_items():
    scraper = IndeedRSSScraper(keywords=["Python", "FastAPI"], max_results=10)
    mock_client = AsyncMock()
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.content = _INDEED_RSS
    mock_client.get = AsyncMock(return_value=resp)

    with patch("app.services.scrapers.rss.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        jobs = await scraper.fetch()

    # RSS scraper doesn't filter by keyword — returns all items up to max
    assert len(jobs) == 2
    assert jobs[0].title == "Python Developer"
    assert jobs[0].company == "Acme Inc"
    assert jobs[0].location == "Remote"
    assert jobs[0].source == "indeed_rss"


# ── ScraperService fallback ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scraper_service_returns_mock_when_all_fail():
    from app.services.scraper import ScraperService

    with patch("app.services.scraper.HNScraper.fetch", side_effect=RuntimeError("HN down")), \
         patch("app.services.scraper.RemoteOKScraper.fetch", side_effect=RuntimeError("ROK down")), \
         patch("app.services.scraper.WeWorkRemotelyScraper.fetch", side_effect=RuntimeError("WWR down")):

        service = ScraperService(keywords=["Python"])
        jobs = await service.scrape()

    assert len(jobs) >= 1
    assert jobs[0].source == "mock"
