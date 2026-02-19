"""Google Maps Lead Generator - A library for scraping business leads from Google Maps."""

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

from .scraper import scrape, collect_lead_links, extract_lead_data, process_all_leads
from .config import TARGET_LEADS, MAX_TABS, HEADLESS, SAVE_AS_CSV, CSV_FILENAME, DEBUG

__all__ = [
    "scrape",
    "collect_lead_links",
    "extract_lead_data",
    "process_all_leads",
    "TARGET_LEADS",
    "MAX_TABS",
    "HEADLESS",
    "SAVE_AS_CSV",
    "CSV_FILENAME",
    "DEBUG",
]
