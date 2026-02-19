"""CLI entry point for Google Maps Lead Generator."""

import argparse
import asyncio
import csv
import json
import logging
import sys

from src.scraper import scrape
from src.config import SAVE_AS_CSV, CSV_FILENAME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def save_to_csv(results: list[dict], filename: str = CSV_FILENAME):
    """Save results to CSV file."""
    if not results:
        return
    field_names = results[0].keys()
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(results)
    logger.info(f"Data saved to {filename}")


async def main():
    parser = argparse.ArgumentParser(
        description="Google Maps Lead Generator - Extract business leads from Google Maps"
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Search query (e.g., 'Restaurants in San Francisco')",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="scraped_data.csv",
        help="Output CSV filename",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON to stdout",
    )
    parser.add_argument(
        "--leads",
        type=int,
        default=25,
        help="Number of leads to collect",
    )

    args = parser.parse_args()

    if args.query is None:
        parser.print_help()
        sys.exit(0)

    logger.info(f"Starting lead generation for: {args.query}")
    results = await scrape(args.query)

    if results:
        logger.info(f"Total leads extracted: {len(results)}")

        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            save_to_csv(results, args.output)
    else:
        logger.warning("No results found")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
