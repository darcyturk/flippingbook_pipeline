# src/config.py
from pathlib import Path

CATALOG_ID = "890674106"
BASE_URL = "https://online.flippingbook.com/view/"
SRC_PATH = Path(__file__).parent
DATA_PATH = SRC_PATH.parent / "data"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
VIEWPORT = {"width": 1920, "height": 1080}
REQUEST_TIMEOUT = 60000 # This is 60 seconds for Playwright. Keep it as 60000 for Playwright.