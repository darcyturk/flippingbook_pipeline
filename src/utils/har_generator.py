# src/utils/har_generator.py
import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__) # Use the existing root logger config from run_extractor.py

async def generate_har(url: str, output_file: Path, timeout_ms: int = 60000):
    """
    Navigates to a given URL with Playwright, waits for network idle,
    and records all network activity to a HAR file.
    """
    logger.info(f"Starting HAR generation for URL: {url}")
    logger.info(f"Output HAR file: {output_file}")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            logger.debug("Browser launched for HAR generation.")
            
            context = await browser.new_context(
                record_har_path=output_file,
                record_har_omit_content=False,
                record_har_mode="full"
            )
            logger.debug("Browser context created with HAR recording enabled.")
            
            page = await context.new_page()
            logger.debug("New page opened for HAR generation.")
            
            try:
                logger.info(f"Navigating to {url}, waiting until networkidle (timeout: {timeout_ms/1000}s)...")
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                
                logger.info("Waiting for an additional 5 seconds to ensure all dynamic content loads for HAR...")
                await page.wait_for_timeout(5000) # 5000ms = 5 seconds
                
                logger.info("Page loaded and additional wait completed for HAR.")

            except Exception as e:
                logger.error(f"Error navigating to {url} during HAR generation: {e}")
            
            logger.debug("Closing browser context to finalize HAR file...")
            await context.close() # Closes context, which finalizes HAR
            logger.debug("Closing browser for HAR generation...")
            await browser.close()
            logger.info("HAR generation complete.")

    except Exception as e:
        logger.critical(f"An unexpected error occurred during HAR generation: {e}", exc_info=True)

