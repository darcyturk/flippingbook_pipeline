# src/pipeline/steps.py
import asyncio
import logging
from pathlib import Path
import json
from PIL import Image
from typing import List, Dict
import concurrent.futures
from functools import partial
from .. import config
from ..delegates import FileManagerDelegate, WebScraperDelegate, DownloaderDelegate, OCRDelegate

logger = logging.getLogger(__name__)

def process_single_task(task: Dict, ocr_delegate: OCRDelegate, file_manager: FileManagerDelegate) -> str:
    """Helper function for Step 3: Contains logic to process ONE OCR task."""
    image_path = Path(task["image_path_str"])
    product_key = task['product_key']
    try:
        with Image.open(image_path) as img:
            details = ocr_delegate.extract_details_from_image(img.copy(), task)
            if details:
                file_manager.save_product_details(details)
                return f"SUCCESS: {product_key}"
    except FileNotFoundError: return f"ERROR: Image not found for {product_key}"
    except Exception as e: return f"ERROR: Failed processing {product_key} due to {e}"
    return f"WARN: No details extracted for {product_key}"

async def step_1_capture_pager_data(web_scraper: WebScraperDelegate, file_manager: FileManagerDelegate) -> Path:
    """Extractor logic for Step 1."""
    logger.info("--- STEP 1: CAPTURING PAGER DATA ---")
    raw_data = await web_scraper.capture_catalog_data(f"{config.BASE_URL}{config.CATALOG_ID}/1", config.TARGET_DOMAIN, config.REQUEST_TIMEOUT)
    if not raw_data: return None
    pager_path = file_manager.save_pager_json(raw_data, config.CATALOG_ID)
    logger.info("--- STEP 1 COMPLETE ---")
    return pager_path

def step_2_process_pages_and_images(pager_path: Path, downloader: DownloaderDelegate, file_manager: FileManagerDelegate):
    """Extractor logic for Step 2."""
    logger.info("--- STEP 2: GENERATING IMAGES AND OCR TASKS ---")
    with pager_path.open("r") as f: catalog_data = json.load(f)
    ocr_tasks = []
    for page_data in catalog_data.get("pages", []):
        page_key = page_data.get("id")
        if not (isinstance(page_data, dict) and page_key): continue
        logger.info("Processing page: %s", page_key)
        file_manager.save_page_layout(page_data, config.CATALOG_ID, page_key)
        page_image = downloader.download_page_image(page_data.get("url"))
        if not page_image:
            logger.warning("Skipping page %s, image download failed.", page_key)
            continue
        links = [link for link in page_data.get("links", []) if 'product' in link.get('url', '')]
        logger.info("Found %s products. Creating images and tasks...", len(links))
        for i, link in enumerate(links):
            rect, url = link.get('rect'), link.get('url')
            if not rect or len(rect) != 4 or not url: continue
            product_key = f"{page_key}_prod_{i+1}"
            cropped_image = page_image.crop((rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3]))
            image_path = file_manager.save_product_image(cropped_image, config.CATALOG_ID, page_key, product_key)
            ocr_tasks.append({"image_path_str": str(image_path), "catalog_id": config.CATALOG_ID, "page_key": page_key, "product_key": product_key, "product_url": url})
    file_manager.save_ocr_task_list(ocr_tasks)
    logger.info("--- STEP 2 COMPLETE ---")

def step_3_perform_ocr(file_manager: FileManagerDelegate, ocr_delegate: OCRDelegate):
    """Extractor logic for Step 3."""
    logger.info("--- STEP 3: PERFORMING OCR ON PRODUCT IMAGES (IN PARALLEL) ---")
    tasks = file_manager.read_ocr_task_list()
    if not tasks:
        logger.warning("No OCR tasks found. Exiting step.")
        return
    logger.info("Found %s product images. Distributing tasks across available CPU cores...", len(tasks))
    worker_function = partial(process_single_task, ocr_delegate=ocr_delegate, file_manager=file_manager)
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = list(executor.map(worker_function, tasks))
    for result in results:
        if "SUCCESS" in result: logger.info("OCR Result -> %s", result)
        elif "WARN" in result: logger.warning("OCR Result -> %s", result)
        elif "ERROR" in result: logger.error("OCR Result -> %s", result)
    logger.info("--- STEP 3 COMPLETE ---")
