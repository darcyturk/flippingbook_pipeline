# src/delegates/__init__.py

# This file makes the delegate classes directly available from the 'delegates' package.
# Instead of: from src.delegates.web_scraper_delegate import WebScraperDelegate
# We can now use: from src.delegates import WebScraperDelegate

from .web_scraper_delegate import WebScraperDelegate
from .downloader_delegate import DownloaderDelegate
from .file_manager_delegate import FileManagerDelegate
from .ocr_delegate import OCRDelegate
