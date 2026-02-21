"""Google Maps Lead Generator - A library for scraping business leads."""

__version__ = "0.1.0"
__author__ = "Your Name"
__license__ = "MIT"

from .config import CSV_FILENAME, DEBUG, HEADLESS, MAX_TABS, SAVE_AS_CSV, TARGET_LEADS
from .scraper import collect_lead_links, extract_lead_data, process_all_leads, scrape

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
