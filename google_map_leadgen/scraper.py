"""
Google Maps Lead Scraper
========================

A high-performance library for extracting business leads from Google Maps.

Architecture:
    1. collect_lead_links()  - Scrolls Maps feed, collects place URLs
    2. extract_lead_data()   - Navigates to place page and extracts data
    3. _page_worker()        - Manages a persistent browser tab
    4. process_all_leads()  - Creates N workers to process URLs concurrently
    5. scrape()             - Main orchestrator

Performance Optimizations:
    - Phase 1: No route interception for faster initial load
    - Phase 2: Blocks images/media/fonts to reduce bandwidth
    - Single page.evaluate() replaces multiple round-trips
    - Page pooling: Tabs are reused instead of created/destroyed per URL
    - Minimal viewport (800x600) reduces rendering overhead
    - JS-level link extraction avoids multiple query_selector calls
"""

import asyncio
import logging

from camoufox.async_api import AsyncCamoufox

from .config import HEADLESS, MAX_TABS, TARGET_LEADS

logger = logging.getLogger(__name__)

_BLOCKED_RESOURCE_TYPES = frozenset(("image", "media", "font", "ping", "websocket"))


async def _block_heavy_resources(route):
    """Abort heavy resources (images, media, fonts) to improve performance."""
    if route.request.resource_type in _BLOCKED_RESOURCE_TYPES:
        await route.abort()
    else:
        await route.continue_()


_EXTRACT_DATA_JS = """
() => {
    const h1 = document.querySelector('h1.DUwDvf');
    if (!h1) return null;
    const getText = el => {
        if (!el) return 'N/A';
        return el.innerText.replace(/\\n/g, ' ').trim();
    };
    return {
        name:    h1.innerText.trim(),
        address: getText(document.querySelector('button[data-item-id="address"]')),
        phone:   getText(document.querySelector('button[data-item-id^="phone:tel:"]')),
        website: getText(document.querySelector('a[data-item-id="authority"]')),
    };
}
"""

_COLLECT_LINKS_JS = """
() => {
    const anchors = document.querySelectorAll('a[href*="/maps/place/"]');
    return [...anchors].map(a => a.href).filter(Boolean);
}
"""


async def collect_lead_links(
    browser, query: str, target: int = TARGET_LEADS
) -> list[str]:
    """
    Search Google Maps for a query and collect place URLs.

    Args:
        browser: Camoufox browser instance
        query: Search query (e.g., "Mobile Repair Shop in New York")
        target: Maximum number of lead URLs to collect

    Returns:
        List of unique Google Maps place URLs
    """
    page = await browser.new_page(viewport={"width": 800, "height": 600})
    search_url = (
        f"https://www.google.com/maps/search/{query.replace(' ', '+')}?entry=ttu"
    )

    await page.goto(search_url, wait_until="domcontentloaded", timeout=60_000)

    try:
        await page.wait_for_selector('div[role="feed"]', timeout=30_000)
    except Exception:
        logger.warning("Failed to load results feed")
        await page.close()
        return []

    update_btn = page.get_by_role("checkbox", name="Update results when map moves")
    is_checked = (await update_btn.get_attribute("aria-checked")) == "true"
    await update_btn.click();

    lead_links: set[str] = set()
    stale_rounds = 0
    max_stale = 5

    while len(lead_links) < target and stale_rounds < max_stale:
        prev_count = len(lead_links)
        hrefs = await page.evaluate(_COLLECT_LINKS_JS)
        lead_links.update(hrefs)

        if len(lead_links) == prev_count:
            stale_rounds += 1
        else:
            stale_rounds = 0

        if len(lead_links) >= target:
            break

        scroll_js = (
            "() => { const feed = document.querySelector('div[role=\"feed\"]'); "
            "if (feed) feed.scrollTop = feed.scrollHeight; }"
        )
        await page.evaluate(scroll_js)
        await asyncio.sleep(0.8)

    await page.close()
    return list(lead_links)[:target]


async def extract_lead_data(page, url: str) -> dict | None:
    """
    Navigate to a place URL and extract business data.

    Args:
        page: Camoufox page instance
        url: Google Maps place URL

    Returns:
        Dictionary with name, address, phone, website or None if failed
    """
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_selector("h1.DUwDvf", timeout=15_000)
        data = await page.evaluate(_EXTRACT_DATA_JS)
        return data if data else None
    except Exception as exc:
        logger.debug(f"Failed to extract data from {url}: {exc}")
        return None


async def _page_worker(
    page,
    url_queue: asyncio.Queue,
    results: list,
    total: int,
    counter: dict,
):
    """
    Worker that owns a persistent page and processes URLs from queue.

    Args:
        page: Camoufox page instance
        url_queue: Queue of URLs to process
        results: List to append successful results
        total: Total number of URLs to process
        counter: Shared counter for progress tracking
    """
    while True:
        try:
            url = url_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        counter["n"] += 1
        data = await extract_lead_data(page, url)
        if data:
            results.append(data)

        url_queue.task_done()


async def process_all_leads(
    browser, urls: list[str], max_tabs: int = MAX_TABS
) -> list[dict]:
    """
    Process multiple URLs concurrently using a pool of persistent pages.

    Args:
        browser: Camoufox browser instance
        urls: List of place URLs to scrape
        max_tabs: Maximum number of concurrent tabs

    Returns:
        List of dictionaries containing business data
    """
    num_tabs = min(max_tabs, len(urls))

    url_queue: asyncio.Queue[str] = asyncio.Queue()
    for url in urls:
        url_queue.put_nowait(url)

    results: list[dict] = []
    counter = {"n": 0}

    pages = []
    for _ in range(num_tabs):
        p = await browser.new_page(viewport={"width": 800, "height": 600})
        await p.route("**/*", _block_heavy_resources)
        pages.append(p)

    tasks = [
        asyncio.create_task(_page_worker(page, url_queue, results, len(urls), counter))
        for page in pages
    ]

    await asyncio.gather(*tasks)

    for p in pages:
        try:
            await p.close()
        except Exception:
            pass

    return results


async def scrape(
    query: str, target: int = TARGET_LEADS, max_tabs: int = MAX_TABS
) -> list[dict]:
    """
    Main entry point - scrape business leads from Google Maps.

    Args:
        query: Search query (e.g., "Restaurants in San Francisco")
        target: Number of leads to collect
        max_tabs: Number of concurrent browser tabs

    Returns:
        List of dictionaries containing:
            - name: Business name
            - address: Physical address
            - phone: Phone number
            - website: Website URL
    """
    async with AsyncCamoufox(headless=HEADLESS) as browser:
        lead_urls = await collect_lead_links(browser, query, target=target)
        if not lead_urls:
            logger.info("No leads found for query")
            return []

        results = await process_all_leads(browser, lead_urls, max_tabs=max_tabs)
        logger.info(f"Scraped {len(results)}/{len(lead_urls)} leads successfully")
        return results
