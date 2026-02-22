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
from contextlib import suppress

from camoufox.async_api import AsyncCamoufox

from .config import HEADLESS, MAX_TABS, TARGET_LEADS

logger = logging.getLogger(__name__)

_BLOCKED_RESOURCE_TYPES = frozenset(("image", "media", "font", "ping", "websocket"))
_WAIT_SLICE_SECONDS = 2
_NAVIGATION_TIMEOUT_MS = 45_000
_DETAIL_SELECTOR_TIMEOUT_MS = 30_000


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


async def _wait_in_slices(task: asyncio.Task, total_timeout_ms: int) -> bool:
    """
    Wait for a task in short slices to avoid one large static timeout.

    Returns:
        True if task finished before timeout, False if timed out.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + (total_timeout_ms / 1000)

    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await task
            return False

        try:
            await asyncio.wait_for(
                asyncio.shield(task),
                timeout=min(_WAIT_SLICE_SECONDS, remaining),
            )
            return True
        except TimeoutError:
            continue


async def collect_lead_links(
    browser,
    query: str,
    target: int = TARGET_LEADS,
    url_queue: asyncio.Queue[str | None] | None = None,
) -> list[str]:
    """
    Search Google Maps for a query and collect place URLs.

    Args:
        browser: Camoufox browser instance
        query: Search query (e.g., "Mobile Repair Shop in New York")
        target: Maximum number of lead URLs to collect
        url_queue: Optional queue to stream newly found URLs to consumers

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
    if asyncio.iscoroutine(update_btn):
        update_btn = await update_btn

    is_clicked = await update_btn.click()
    if is_clicked:
        with suppress(Exception):
            await update_btn.click()

    lead_links: set[str] = set()
    stale_rounds = 0
    max_stale = 5

    while len(lead_links) < target and stale_rounds < max_stale:
        hrefs = await page.evaluate(_COLLECT_LINKS_JS)
        new_links = 0

        for href in hrefs:
            if href in lead_links:
                continue

            lead_links.add(href)
            new_links += 1

            if url_queue is not None:
                await url_queue.put(href)

            if len(lead_links) >= target:
                break

        if new_links == 0:
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
        navigation_task = asyncio.create_task(
            page.goto(url, wait_until="domcontentloaded", timeout=0)
        )
        if not await _wait_in_slices(
            navigation_task, total_timeout_ms=_NAVIGATION_TIMEOUT_MS
        ):
            logger.debug(f"Timed out while loading {url}")
            return None

        selector_task = asyncio.create_task(
            page.wait_for_selector("h1.DUwDvf", timeout=0)
        )
        if not await _wait_in_slices(
            selector_task, total_timeout_ms=_DETAIL_SELECTOR_TIMEOUT_MS
        ):
            logger.debug(f"Timed out waiting for data on {url}")
            return None

        data = await page.evaluate(_EXTRACT_DATA_JS)
        return data if data else None
    except Exception as exc:
        logger.debug(f"Failed to extract data from {url}: {exc}")
        return None


async def _page_worker(
    page,
    url_queue: asyncio.Queue[str | None],
    results: list,
):
    """
    Worker that owns a persistent page and processes URLs from queue.

    Args:
        page: Camoufox page instance
        url_queue: Queue of URLs to process
        results: List to append successful results
    """
    while True:
        url = await url_queue.get()
        try:
            if url is None:
                return

            data = await extract_lead_data(page, url)
            if data:
                results.append(data)
        finally:
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
    if not urls:
        return []

    num_tabs = max(1, min(max_tabs, len(urls)))

    url_queue: asyncio.Queue[str | None] = asyncio.Queue()
    for url in urls:
        url_queue.put_nowait(url)
    for _ in range(num_tabs):
        url_queue.put_nowait(None)

    results: list[dict] = []

    pages = []
    for _ in range(num_tabs):
        p = await browser.new_page(viewport={"width": 800, "height": 600})
        await p.route("**/*", _block_heavy_resources)
        pages.append(p)

    tasks = [
        asyncio.create_task(_page_worker(page, url_queue, results)) for page in pages
    ]

    await url_queue.join()
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
    if target <= 0:
        return []

    async with AsyncCamoufox(headless=HEADLESS) as browser:
        num_tabs = max(1, min(max_tabs, target))
        url_queue: asyncio.Queue[str | None] = asyncio.Queue()
        results: list[dict] = []

        lead_urls = await collect_lead_links(
            browser, query, target=target, url_queue=url_queue
        )

        pages = []
        for _ in range(num_tabs):
            page = await browser.new_page(viewport={"width": 800, "height": 600})
            await page.route("**/*", _block_heavy_resources)
            pages.append(page)

        tasks = [
            asyncio.create_task(_page_worker(page, url_queue, results))
            for page in pages
        ]

        for _ in range(num_tabs):
            await url_queue.put(None)

        await url_queue.join()
        await asyncio.gather(*tasks)

        for page in pages:
            with suppress(Exception):
                await page.close()

        if not lead_urls:
            logger.info("No leads found for query")
            return []

        logger.info(f"Scraped {len(results)}/{len(lead_urls)} leads successfully")
        return results
