from app.services.scrapers.base import ScraperBase, ScrapedJob
from app.services.scrapers.hn import HNScraper
from app.services.scrapers.remoteok import RemoteOKScraper
from app.services.scrapers.rss import IndeedRSSScraper, WeWorkRemotelyScraper

__all__ = [
    "ScraperBase", "ScrapedJob",
    "HNScraper", "RemoteOKScraper",
    "WeWorkRemotelyScraper", "IndeedRSSScraper",
]
