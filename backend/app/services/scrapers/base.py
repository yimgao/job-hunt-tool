"""Base scraper interface — all scrapers implement this."""
from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ScrapedJob:
    """Normalized job record before DB insertion."""
    title: str
    company: str
    jd_text: str
    source: str
    source_id: str
    location: str = "Remote / USA"
    url: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    posted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    skills: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        text = f"{self.title}|{self.company}|{self.jd_text[:500]}"
        return hashlib.sha256(text.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "company": self.company,
            "jd_text": self.jd_text,
            "source": self.source,
            "source_id": self.source_id,
            "location": self.location,
            "url": self.url,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "posted_at": self.posted_at.isoformat(),
            "content_hash": self.content_hash,
            "skills": self.skills,
        }


def _clean(text: str | None) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_salary(text: str) -> tuple[int | None, int | None]:
    """Extract (min, max) salary in USD from free text. Returns (None, None) if not found."""
    text = text.replace(",", "").replace("$", "")
    pattern = r"(\d{2,3})k?\s*[-–to]+\s*(\d{2,3})k?"
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo < 1000:
            lo *= 1000
        if hi < 1000:
            hi *= 1000
        return lo, hi
    single = re.search(r"(\d{2,3})k", text, re.IGNORECASE)
    if single:
        val = int(single.group(1)) * 1000
        return val, None
    return None, None


ENTRY_LEVEL_TERMS = {
    "entry level", "entry-level", "junior", "new grad", "new graduate",
    "0-2 years", "0-1 year", "recent graduate", "associate", "intern",
}


def is_entry_level(title: str, jd_text: str) -> bool:
    """Heuristic: return True if the job appears entry-level."""
    combined = (title + " " + jd_text).lower()
    return any(term in combined for term in ENTRY_LEVEL_TERMS)


class ScraperBase(ABC):
    """All scrapers must implement fetch()."""

    source_name: str = "unknown"

    def __init__(self, keywords: list[str], max_results: int = 30):
        self.keywords = keywords
        self.max_results = max_results

    @abstractmethod
    async def fetch(self) -> list[ScrapedJob]:
        """Return a list of raw jobs. No dedup — caller handles that."""
        ...
