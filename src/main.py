# src/main.py
import logging
from typing import List, Dict
from pathlib import Path
from . import config
from .delegates import FileManagerDelegate, WebScraperDelegate, DownloaderDelegate
from .pipeline.steps import step_1_extract_model_from_html, step_2_extract_product_data

logger = logging.getLogger(__name__)

async def main(steps_to_run: List[int]):
    """The main orchestrator, updated for the direct HTML parsing method."""
    
    file_manager = FileManagerDelegate(base_path=config.DATA_PATH)
    pager_path = file_manager.pager_path / f"pager_{config.CATALOG_ID}.json"

    har_file_path = config.DATA_PATH / f"catalog_{config.CATALOG_ID}.har"
    logger.info("HAR file will be saved to: %s", har_file_path)

    signed_params: Dict[str, str] = {} # Initialize for scope

    if 1 in steps_to_run:
        async with WebScraperDelegate(
            user_agent=config.USER_AGENT, 
            viewport=config.VIEWPORT, 
            har_output_path=har_file_path
        ) as web_scraper:
            result = await step_1_extract_model_from_html(web_scraper, file_manager)
            if result is None:
                logger.error("Step 1 failed to extract model or signed parameters. Cannot proceed to Step 2.")
                return 
            
            pager_path, signed_params = result # Unpack the results
            
            if not pager_path.exists():
                logger.error("Step 1 was run, but publication model file was not created. Cannot proceed to Step 2.")
                return 
    else:
        # If step 1 is skipped, attempt to load publication model from disk
        if not pager_path.exists():
            logger.error("Cannot run Step 2: Extracted model JSON from Step 1 not found. Please run Step 1 first (e.g., without --steps 2).")
            return
        
        logger.warning("Step 1 skipped. Attempting to get signed parameters for Step 2.")
        
        # --- IMPORTANT: Fallback for signed_params if Step 1 is skipped ---
        # If you run Step 2 directly, these parameters are not extracted by Step 1.
        # You MUST provide them here if they are dynamic.
        # For temporary testing, you can put the values you found in the HAR file here.
        # For a production setup, if they are dynamic per session, you'd need a mechanism
        # to either always run Step 1, or persist/load these parameters.
        
        # You should replace these placeholders with the actual values from your HAR if testing --steps 2 only.
        signed_params = {
            "Policy": "REPLACE_WITH_POLICY_FROM_HAR",
            "Signature": "REPLACE_WITH_SIGNATURE_FROM_HAR",
            "Key-Pair-Id": "REPLACE_WITH_KEY_PAIR_ID_FROM_HAR",
            "uni": "REPLACE_WITH_UNI_FROM_HAR"
        }
        logger.debug("Signed parameters initialized from fallback (if Step 1 skipped): %s", signed_params)
        # --- END Fallback ---

    if 2 in steps_to_run:
        # DownloaderDelegate also needs an __aenter__/__aexit__ if it uses httpx.AsyncClient as a context manager
        # If DownloaderDelegate's client is created in __init__ and not managed as context manager,
        # you might need to manage it manually or make DownloaderDelegate itself an async context manager.
        # The provided DownloaderDelegate *is* an async context manager.
        async with DownloaderDelegate(user_agent=config.USER_AGENT) as downloader:
            await step_2_extract_product_data(pager_path, downloader, file_manager, signed_params)
            
    else:
        logger.info("Step 2 skipped as per --steps argument.")

    logger.info("Main pipeline process finished.")