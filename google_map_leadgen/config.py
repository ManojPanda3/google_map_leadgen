"""
Configuration settings for Google Maps Lead Generator.

Environment Variables:
    LEADS: Number of leads to collect (default: 25)
    MAX_TAB_ALLOWED: Maximum concurrent tabs (default: 2)
    HEADLESS: Run browser in headless mode (default: true)
"""

import os

# Scraper Settings
TARGET_LEADS = int(os.getenv("LEADS", "25"))
MAX_TABS = int(os.getenv("MAX_TAB_ALLOWED", "2"))
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

# Output Settings
SAVE_AS_CSV = True
CSV_FILENAME = "scraped_data.csv"

# Development Settings
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
