# src/delegates/downloader_delegate.py
import logging
import httpx # Assuming you are using httpx for async requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class DownloaderDelegate:
    """Handles downloading various content (XML, images, etc.)."""
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        # httpx.AsyncClient should be created and managed as an async context manager
        # or its close() method called explicitly. Using __aenter__/__aexit__ is best.
        self.client = None # Will be initialized in __aenter__

    async def __aenter__(self):
        # Initialize httpx.AsyncClient here so it's managed by the async with
        self.client = httpx.AsyncClient(headers={"User-Agent": self.user_agent})
        # If you need to explicitly enter the client's context, do so here:
        # await self.client.__aenter__() # This is not strictly necessary if client is new
        logger.debug("DownloaderDelegate httpx.AsyncClient initialized.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose() # Use aclose() for async clients
            logger.debug("DownloaderDelegate httpx.AsyncClient closed.")

    async def download_xml_content(self, url: str, headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Downloads XML content from a URL."""
        if not self.client:
            logger.error("HTTP client not initialized. Cannot download XML.")
            return None
            
        try:
            request_headers = self.client.headers.copy() # Start with default headers
            if headers:
                request_headers.update(headers) # Overlay with provided headers
                
            logger.debug("Attempting to download XML from: %s with headers: %s", url, request_headers)
            
            # Use httpx.get with all parameters
            response = await self.client.get(url, headers=request_headers, follow_redirects=True, timeout=10) # 10 sec timeout for XML
            response.raise_for_status() # Raise an exception for 4xx/5xx responses
            
            logger.debug("Successfully downloaded XML from %s", url)
            return response.text
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error downloading XML from %s: %s - Response: %s", url, e, e.response.text[:200])
        except httpx.RequestError as e:
            logger.error("Network error downloading XML from %s: %s", url, e)
        except Exception as e:
            logger.error("An unexpected error occurred while downloading XML from %s: %s", url, e)
        return None

    # You might have other download methods here later (e.g., download_image)
