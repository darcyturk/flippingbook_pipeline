# src/delegates/web_scraper_delegate.py
import logging
from playwright.async_api import async_playwright, Playwright, BrowserContext, Request, Route
from typing import Dict, Union, Optional
from pathlib import Path
from urllib.parse import urlparse, parse_qs # Required for parsing URL query strings

logger = logging.getLogger(__name__)

class WebScraperDelegate:
    """Handles fetching the raw HTML content of the viewer page."""
    def __init__(self, user_agent: str, viewport: Dict, har_output_path: Path):
        self.user_agent = user_agent
        self.viewport = viewport
        self.har_output_path = har_output_path
        self._playwright: Optional[Playwright] = None
        self._browser = None
        self._context: Optional[BrowserContext] = None
        # NEW: Store captured signed parameters, initialized to empty
        self._captured_signed_params: Dict[str, str] = {} 
        self._interception_active = False # Flag to manage listener state

    async def __aenter__(self):
        logger.debug("Starting Playwright and launching browser...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        
        logger.debug("Creating browser context and enabling HAR recording to: %s", self.har_output_path)
        self._context = await self._browser.new_context(
            user_agent=self.user_agent,
            viewport=self.viewport,
            record_har_path=self.har_output_path,
            record_har_omit_content=False,
            record_har_mode="full" # Capture full details for HAR analysis
        )
        
        # --- CRITICAL CHANGE: Set up request interception for the context ---
        # This route pattern will match any request ending with '.xml' within the 'flash/search/' path
        await self._context.route("**/flash/search/*.xml**", self._handle_xml_request)
        self._interception_active = True
        logger.debug("Playwright browser launched, context created, and XML request interception enabled.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Closing browser, context, and stopping Playwright to finalize HAR...")
        # CRITICAL: Unroute the request handler before closing context to prevent errors
        if self._context and self._interception_active:
            await self._context.unroute("**/flash/search/*.xml**", self._handle_xml_request)
            self._interception_active = False

        if self._context:
            await self._context.close() # This will finalize the HAR file
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.debug("Playwright resources released.")

    async def _handle_xml_request(self, route: Route):
        """
        Intercepts XML requests to capture CloudFront signed URL parameters.
        This method is called by Playwright for matching requests.
        """
        request = route.request
        
        # Only capture if parameters are not already found, to get the first one (they should be identical)
        if not all(k in self._captured_signed_params and self._captured_signed_params[k] for k in ["Policy", "Signature", "Key-Pair-Id", "uni"]):
            parsed_url = urlparse(request.url)
            query_params = parse_qs(parsed_url.query) # Parse query string into a dict

            # Extract parameters, handling potential absence (returns None if not found)
            policy = query_params.get("Policy", [None])[0]
            signature = query_params.get("Signature", [None])[0]
            key_pair_id = query_params.get("Key-Pair-Id", [None])[0]
            uni = query_params.get("uni", [None])[0]

            if all([policy, signature, key_pair_id, uni]):
                self._captured_signed_params = {
                    "Policy": policy,
                    "Signature": signature,
                    "Key-Pair-Id": key_pair_id,
                    "uni": uni
                }
                logger.info(f"Intercepted and captured all signed params for XML request: {request.url}")
                logger.debug(f"Captured params: {self._captured_signed_params}")
                
                # Optional: If you only need them from the very first XML request,
                # you can unroute immediately after capturing to stop listening.
                # await route.page.context.unroute("**/flash/search/*.xml**", self._handle_xml_request)
                # self._interception_active = False
            else:
                logger.debug(f"Intercepted XML request, but some signed params were missing in URL: {request.url}")
        
        await route.continue_() # IMPORTANT: Always continue the request so the page can load!

    async def get_page_html(self, url: str, timeout: int) -> Union[str, None]:
        """
        Navigates to the specified URL using Playwright and returns its full HTML content.
        This will also trigger the XML requests that we are intercepting.
        """
        if not self._context:
            logger.error("Browser context not initialized. Cannot fetch page HTML.")
            return None

        # Reset captured params before navigating to a new main page, to ensure fresh capture
        self._captured_signed_params = {} 
        
        page = await self._context.new_page()
        html_content = None
        try:
            logger.info("Navigating to catalog: %s", url)
            logger.debug("Playwright page.goto timeout parameter received: %s ms (Type: %s)", timeout, type(timeout))
            
            # Use 'domcontentloaded' for initial load, then 'networkidle' for dynamic content
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            logger.debug("Waiting for network idle state to ensure all requests (including XMLs) are made...")
            await page.wait_for_load_state("networkidle") 
            logger.debug("Network idle state reached.")

            html_content = await page.content()
            logger.info("Successfully fetched page HTML content for %s.", url)
        except Exception as e:
            logger.error("Failed to load page HTML from %s: %s", url, e)
        finally:
            if page:
                await page.close()
        return html_content

    def get_captured_signed_params(self) -> Dict[str, str]:
        """
        Retrieves the CloudFront signed parameters captured by the request interceptor.
        """
        return self._captured_signed_params.copy() # Return a copy to prevent external modification