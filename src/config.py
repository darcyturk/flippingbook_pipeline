# src/config.py

# Import the 'Path' object for handling file paths in a way that works on any OS (Windows, macOS, Linux)
from pathlib import Path

# --- Core Settings ---
# The unique ID of the catalog you want to process. Change this value to run on a different catalog.
CATALOG_ID = "890674106"
# The base URL for the catalog viewer.
BASE_URL = "https://online.flippingbook.com/view/"
# The domain where the catalog's JSON data files are hosted. We use this to filter network requests.
TARGET_DOMAIN = "d17lvj5xn8sco6.cloudfront.net"

# --- File Path Settings ---
# This line gets the path to the directory where this config.py file is located (which is 'src').
SRC_PATH = Path(__file__).parent
# This creates the path to the 'data' directory, which will be located one level above 'src'.
# All our output will be saved here.
DATA_PATH = SRC_PATH.parent / "data"

# --- Browser/Network Settings ---
# The User-Agent string tells the website what kind of browser we are. We use a common one to avoid being blocked.
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
# The size of the virtual browser window.
VIEWPORT = {"width": 1920, "height": 1080}
# The maximum time (in milliseconds) to wait for a page to load before giving up.
REQUEST_TIMEOUT = 60000 # 60 seconds

# --- OCR Settings ---
# These are command-line options we pass to the Tesseract engine.
# --oem 3: Use the default, most modern OCR engine.
# --psm 6: Assume the image is a single uniform block of text (good for our cropped product images).
TESSERACT_PRIMARY_CONFIG = r'--oem 3 --psm 6'

# --- Analysis Settings ---
# A list of known brand names. We can use this to help our text analysis identify brands in the OCR output.
KNOWN_BRANDS = [
    'Espoma', 'Miracle-Gro', 'Scotts', 'Ortho', 'Roundup', 'Bayer', 'Bonide'
]

