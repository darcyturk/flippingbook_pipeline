# src/main.py

import logging
from typing import List

# Import our configuration and all delegates/steps from our organized packages
from . import config
from .delegates import FileManagerDelegate, WebScraperDelegate, DownloaderDelegate, OCRDelegate
from .pipeline import step_1_capture_pager_data, step_2_process_pages_and_images, step_3_perform_ocr

logger = logging.getLogger(__name__)

async def main(steps_to_run: List[int]):
    """The main orchestrator that controls which steps are run based on user input."""
    
    # --- Initialization ---
    # Initialize components that are needed across multiple steps.
    file_manager = FileManagerDelegate(base_path=config.DATA_PATH)
    pager_path = file_manager.pager_path / f"pager_{config.CATALOG_ID}.json"

    # --- Step 1 Execution ---
    if 1 in steps_to_run:
        # Step 1 requires the WebScraperDelegate. We initialize it here and pass it to the step function.
        async with WebScraperDelegate(config.USER_AGENT, config.VIEWPORT) as web_scraper:
            await step_1_capture_pager_data(web_scraper, file_manager)
    
    # --- Step 2 Execution ---
    if 2 in steps_to_run:
        # Before running, check if the output from Step 1 exists.
        if not pager_path.exists():
            logger.error("Cannot run Step 2: Pager data from Step 1 not found. Please run Step 1 first.")
        else:
            # Step 2 requires the DownloaderDelegate.
            downloader = DownloaderDelegate(user_agent=config.USER_AGENT)
            step_2_process_pages_and_images(pager_path, downloader, file_manager)

    # --- Step 3 Execution ---
    if 3 in steps_to_run:
        # Before running, check if the output from Step 2 exists.
        ocr_task_list_path = file_manager.base_path / "ocr_task_list.json"
        if not ocr_task_list_path.exists():
            logger.error("Cannot run Step 3: OCR task list from Step 2 not found. Please run Step 2 first.")
        else:
            # Step 3 requires the OCRDelegate.
            ocr_delegate = OCRDelegate(config.TESSERACT_PRIMARY_CONFIG, config.KNOWN_BRANDS)
            step_3_perform_ocr(file_manager, ocr_delegate)
