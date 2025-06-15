# src/delegates/downloader_delegate.py
import logging
import requests
import io
from PIL import Image
from typing import Dict

logger = logging.getLogger(__name__)

class DownloaderDelegate:
    """Handles simple, direct file downloads via HTTP requests."""
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
    def download_page_image(self, image_url: str) -> Image.Image | None:
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(image_url, headers=headers, timeout=30)
            if response.status_code == 200: return Image.open(io.BytesIO(response.content))
            else: logger.warning("Failed to download image (status %s): %s", response.status_code, image_url)
        except Exception as e: logger.error("Exception during image download from %s: %s", image_url, e)
        return None

