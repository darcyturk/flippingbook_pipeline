# src/delegates/web_scraper_delegate.py

import asyncio
import logging
from playwright.async_api import async_playwright, Route, Request
from typing import Dict

logger = logging.getLogger(__name__)

class WebScraperDelegate:
    """Handles all complex web browser automation and network capture tasks."""
    def __init__(self, user_agent: str, viewport: Dict):
        self.user_agent, self.viewport, self.catalog_data = user_agent, viewport, None
        self._playwright, self._browser = None, None
    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._browser: await self._browser.close()
        if self._playwright: await self._playwright.stop()
    async def _intercept_routes(self, route: Route, request: Request, target_domain: str):
        if target_domain in request.url and "pager.json" in request.url and "/common/" in request.url:
            try:
                response = await route.fetch()
                if response.status == 200:
                    self.catalog_data = await response.json()
                    logger.info("Intercepted main catalog data from: %s", request.url)
                await route.fulfill(response=response)
            except Exception as e:
                logger.error("Error intercepting request: %s", e); await route.continue_()
        else: await route.continue_()
    async def capture_catalog_data(self, catalog_url: str, target_domain: str, timeout: int) -> Dict:
        context = await self._browser.new_context(user_agent=self.user_agent, viewport=self.viewport)
        page = await context.new_page()
        handler = lambda r, req: asyncio.create_task(self._intercept_routes(r, req, target_domain))
        await page.route("**/*", handler)
        try:
            logger.info("Navigating to catalog: %s", catalog_url)
            await page.goto(catalog_url, wait_until="networkidle", timeout=timeout)
            await page.wait_for_timeout(3000)
        except Exception as e: logger.error("Failed to load catalog: %s", e)
        finally: await context.close()
        return self.catalog_data
