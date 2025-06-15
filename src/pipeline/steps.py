# src/pipeline/steps.py
import logging
from pathlib import Path
import json
import json5
from typing import List, Dict, Any, Union, Optional, Tuple
import xml.etree.ElementTree as ET
import re
import asyncio
from rich.logging import RichHandler
from rich.pretty import pprint
from urllib.parse import urljoin, parse_qs, urlparse
from lxml import etree

from .. import config
from ..delegates import FileManagerDelegate, WebScraperDelegate, DownloaderDelegate
from ..models import ProductDetailsAspect

logger = logging.getLogger(__name__)

def find_publication_model(html_content: str) -> Union[Dict, None]:
    """Parses the HTML to find and extract the FBO.PreloadedPublicationModel JSON object."""
    json_string = ""
    try:
        start_marker = "window.FBO.PreloadedPublicationModel = "
        start_index = html_content.find(start_marker)
        if start_index == -1:
            logger.debug("Publication Model start marker not found in HTML.")
            return None
        start_index += len(start_marker)

        end_index = html_content.find(";", start_index)
        if end_index == -1:
            logger.debug("Publication Model end marker not found in HTML.")
            return None

        json_string = html_content[start_index:end_index]

        logger.debug("Extracted potential JSON string (first 500 chars): %s", json_string[:500])
        logger.debug("Full extracted string length: %d", len(json_string))

        parsed_model = json5.loads(json_string)
        logger.debug("Successfully parsed Publication Model.")
        return parsed_model
    except (json5.JSON5DecodeError, IndexError) as e:
        logger.error("Failed to parse Publication Model from HTML: %s", e)
        if isinstance(e, json5.JSON5DecodeError):
            snippet_start = max(0, e.pos - 50)
            snippet_end = e.pos + 50
            snippet_end = min(snippet_end, len(json_string))
            logger.error("Faulty JSON string snippet around char %d: '%s'", e.pos, json_string[snippet_start:snippet_end])
        else:
            logger.error("IndexError occurred, likely in string slicing: %s", e)
    return None

def _extract_signed_cloudfront_params(html_content: str, publication_model: Dict) -> Dict[str, str]:
    """
    Attempts to automatically extract CloudFront signed URL parameters (Policy, Signature, Key-Pair-Id, uni)
    from the HTML content using specific regex patterns.
    """
    signed_params = {}
    
    # Attempt to get 'uni' (RendererVersion) from publication_model first, as it's common.
    uni_val = publication_model.get("Publication", {}).get("RendererVersion")
    if uni_val:
        signed_params["uni"] = uni_val
        logger.debug(f"Found 'uni' from publication model: {uni_val}")
    else:
        logger.warning("'uni' (RendererVersion) not found in publication model.")

    # Regex patterns for the three main parameters
    patterns = {
        "Key-Pair-Id": r"Key-Pair-Id=([A-Z0-9]{16,32})",
        "Policy": r"Policy=([A-Za-z0-9-_=]+)",
        "Signature": r"Signature=([A-Za-z0-9-~_=]+)"
    }

    # Search the entire HTML content for these patterns
    logger.debug("Attempting to find Policy, Signature, Key-Pair-Id using direct regex patterns in HTML content...")
    for key, pattern in patterns.items():
        if key in signed_params and signed_params[key]:
            logger.debug(f"'{key}' already found (value: {signed_params[key][:20]}...). Skipping regex search.")
            continue

        match = re.search(pattern, html_content) # Search entire HTML
        if match:
            signed_params[key] = match.group(1)
            logger.debug(f"FOUND '{key}' from HTML regex: {signed_params[key][:20]}...")
        else:
            logger.debug(f"'{key}' pattern NOT found in HTML using direct regex.")

    # Final check and logging
    required_keys = ["Policy", "Signature", "Key-Pair-Id", "uni"]
    missing_final_keys = [k for k in required_keys if k not in signed_params or not signed_params[k]]

    if missing_final_keys:
        logger.error(f"FINAL CHECK: Critical signed URL parameters are missing: {missing_final_keys}. XML downloads WILL FAIL.")
        logger.debug(f"Current collected signed_params: {signed_params}")
    else:
        logger.info("FINAL CHECK: All CloudFront signing parameters collected successfully.")
        logger.debug("All collected params: %s", signed_params)

    return signed_params

def parse_search_xml(xml_content: str) -> List[Dict]:
    """Parses the search XML content to extract words and their coordinates."""
    texts = []
    if not xml_content:
        logger.debug("No XML content provided for parsing.")
        return texts
    try:
        root = etree.fromstring(xml_content.encode('utf-8'))
        for word in root.xpath('.//w'):
            coords = word.get('c')
            text = word.text
            if coords and text:
                try:
                    x, y, w, h = map(int, coords.split(','))
                    texts.append({'text': text.strip(), 'rect': [x, y, w, h]})
                except (ValueError, IndexError):
                    logger.warning("Could not parse coordinates for word: '%s' with coords '%s'", text, coords)
            else:
                logger.debug("Skipping word due to missing coords or text: %s", etree.tostring(word, encoding='unicode').decode().strip())
    except etree.XMLParseError as e:
        logger.error("Failed to parse search.xml: %s", e)
    return texts

def find_text_near_rect(xml_texts: List[Dict], product_rect: List[int]) -> str:
    """Finds and concatenates text elements near a given product rectangle."""
    px, py, pw, ph = product_rect
    search_x_start, search_x_end = px - pw, px + (pw * 2)
    search_y_start, search_y_end = py - ph, py + (ph * 2)

    nearby_words = []
    for item in xml_texts:
        item_x, item_y = item['rect'][0], item['rect'][1]
        if search_x_start <= item_x <= search_x_end and \
           search_y_start <= item_y <= search_y_end:
            nearby_words.append(item['text'])

    found_text = " ".join(nearby_words)
    logger.debug(f"Found text near rect {product_rect}: '{found_text[:100]}...'")
    return found_text

async def step_1_extract_model_from_html(web_scraper: WebScraperDelegate, file_manager: FileManagerDelegate) -> Optional[Tuple[Path, Dict[str, str]]]:
    """
    Step 1: Extracts the publication model JSON from the HTML.
    Also, it triggers Playwright to capture signed URL parameters via request interception.
    Returns a tuple of (path to saved JSON, dictionary of signed parameters),
    or None if extraction fails.
    """
    logger.info("--- STEP 1: EXTRACTING PUBLICATION MODEL AND CAPTURING SIGNED PARAMS ---")
    initial_url = f"{config.BASE_URL}{config.CATALOG_ID}/1"
    logger.info("Attempting to retrieve HTML from: %s", initial_url)
    
    html_content = await web_scraper.get_page_html(initial_url, config.REQUEST_TIMEOUT)

    if not html_content:
        logger.error("Failed to retrieve HTML content for %s. Exiting pipeline.", initial_url)
        return None

    logger.debug("HTML content retrieved (first 200 chars): %s", html_content[:200])
    publication_model = find_publication_model(html_content)

    if not publication_model:
        logger.error("Failed to extract publication model from HTML for %s. Exiting pipeline.", initial_url)
        return None

    logger.debug("Extracted Publication Model Preview:")
    pprint(publication_model, max_length=10, max_string=100)

    # --- NEW: Extract signed parameters from HTML content and publication model ---
    signed_params = _extract_signed_cloudfront_params(html_content, publication_model)
    
    # Secondary check: If Playwright interception also captured them, prioritize those (more reliable for truly dynamic).
    intercepted_params = web_scraper.get_captured_signed_params()
    if intercepted_params and all(k in intercepted_params and intercepted_params[k] for k in ["Policy", "Signature", "Key-Pair-Id", "uni"]):
        logger.info("Prioritizing signed parameters captured via Playwright interception if complete.")
        signed_params = intercepted_params # Overwrite if interception yielded complete set
    else:
        logger.debug("Playwright interception did not capture a complete set, relying on HTML regex extraction (if any).")
    # --- END NEW ---

    final_required_keys = ["Policy", "Signature", "Key-Pair-Id", "uni"]
    missing_at_end = [k for k in final_required_keys if k not in signed_params or not signed_params[k]]

    if missing_at_end:
        logger.error(f"FINAL WARNING: Critical signed URL parameters are still missing after all extraction attempts: {missing_at_end}. XML downloads WILL FAIL in Step 2.")
        logger.debug(f"Collected params before returning: {signed_params}")
        return None # Indicate failure if crucial params are not found

    saved_path = file_manager.save_extracted_json(publication_model, config.CATALOG_ID)
    logger.info("Publication model saved to: %s", saved_path)
    
    # NEW: Save signed parameters to file
    file_manager.save_signed_params(signed_params, config.CATALOG_ID)
    
    logger.info("--- STEP 1 COMPLETE ---")
    
    return saved_path, signed_params


async def step_2_extract_product_data(pager_path: Path, downloader: DownloaderDelegate, file_manager: FileManagerDelegate, signed_params: Dict[str, str]):
    """
    Step 2: Extracts product data from the publication model and associated XMLs.
    """
    logger.info("--- STEP 2: EXTRACTING PRODUCT DATA FROM XML ---")
    try:
        with pager_path.open("r", encoding="utf-8") as f:
            publication_model = json.load(f)
        logger.debug("Loaded publication model from: %s", pager_path)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("Failed to load publication model from %s: %s. Exiting.", pager_path, e)
        return

    # --- Check for missing params (should be caught by Step 1, but good to re-check) ---
    if not all(k in signed_params and signed_params[k] for k in ["Policy", "Signature", "Key-Pair-Id", "uni"]):
        logger.error("Signed URL parameters are incomplete or missing for Step 2. Cannot download signed XMLs. Parameters: %s", signed_params)
        return # Cannot proceed if parameters are missing

    # Construct the full query string from the extracted parameters
    signed_query_string = f"Policy={signed_params['Policy']}&Signature={signed_params['Signature']}&Key-Pair-Id={signed_params['Key-Pair-Id']}&uni={signed_params['uni']}"
    logger.debug("Using signed query string for XML downloads: %s", signed_query_string)

    content_root = publication_model.get("Publication", {}).get("ContentRoot")
    if not content_root:
        logger.error("Could not determine ContentRoot from publication model. Exiting.")
        return

    logger.info("ContentRoot used for base search URL: %s", content_root)

    # --- CRITICAL CHANGE: Refine all_pages_with_xml_paths extraction ---
    all_pages_with_xml_paths = []
    pages_data_from_model = publication_model.get("Publication", {}).get("pages", {})
    
    logger.debug("Attempting to discover pages from model 'pages' key...")
    if isinstance(pages_data_from_model, dict):
        logger.debug(f"Found 'pages' as a dictionary with {len(pages_data_from_model)} entries.")
        for page_key_id, page_obj in pages_data_from_model.items():
            logger.debug(f"Processing page dictionary entry for key '{page_key_id}'.")
            if isinstance(page_obj, dict) and page_obj.get("id"):
                search_path = page_obj.get("search", {}).get("path")
                if search_path:
                    all_pages_with_xml_paths.append({
                        "page_key": page_obj["id"],
                        "search_xml_relative_path": search_path,
                        "page_data": page_obj
                    })
                    logger.debug(f"Found page '{page_key_id}' with search path: {search_path}")
                else:
                    logger.warning(f"Page '{page_key_id}' is missing 'search.path'. Its structure: {pprint.pformat(page_obj, max_depth=2, max_length=50)}. Skipping.")
            else:
                logger.warning(f"Skipping malformed page entry (not a dict or missing 'id') for key '{page_key_id}': {pprint.pformat(page_obj, max_depth=1, max_length=50)}.")
    elif isinstance(pages_data_from_model, list):
        logger.debug(f"Found 'pages' as a list with {len(pages_data_from_model)} entries.")
        for idx, page_obj in enumerate(pages_data_from_model):
            logger.debug(f"Processing page list entry at index {idx}.")
            if isinstance(page_obj, dict) and page_obj.get("id"):
                search_path = page_obj.get("search", {}).get("path")
                if search_path:
                     all_pages_with_xml_paths.append({
                        "page_key": page_obj["id"],
                        "search_xml_relative_path": search_path,
                        "page_data": page_obj
                    })
                     logger.debug(f"Found page '{page_obj['id']}' with search path: {search_path}")
                else:
                    logger.warning(f"Page with ID '{page_obj.get('id')}' is missing 'search.path'. Its structure: {pprint.pformat(page_obj, max_depth=2, max_length=50)}. Skipping.")
            else:
                logger.warning(f"Skipping malformed page entry (not a dict or missing 'id') at index {idx}: {pprint.pformat(page_obj, max_depth=1, max_length=50)}.")
    else:
        logger.error("Unexpected type for 'pages' data in publication model: %s. Expected dict or list.", type(pages_data_from_model))


    logger.info("Discovered %d pages to process with XML paths.", len(all_pages_with_xml_paths))

    if not all_pages_with_xml_paths:
        logger.warning("No pages with valid search XML paths found. Step 2 will not process any XMLs.")
        logger.info("--- STEP 2 COMPLETE ---")
        return

    for page_info in all_pages_with_xml_paths:
        page_key = page_info["page_key"]
        search_xml_relative_path = page_info["search_xml_relative_path"]
        page_data = page_info["page_data"]

        logger.info("[bold blue]Processing page:[/bold blue] %s", page_key)

        full_xml_base_url = urljoin(content_root, search_xml_relative_path)
        search_xml_url = f"{full_xml_base_url}?{signed_query_string}"

        logger.debug("Attempting to download XML from: %s", search_xml_url)

        download_headers = {"Referer": config.BASE_URL.rstrip('/') + "/"}
        xml_content = await downloader.download_xml_content(search_xml_url, headers=download_headers)

        if not xml_content:
            logger.warning("No XML content downloaded for page %s from %s, skipping.", page_key, search_xml_url)
            continue

        file_manager.save_search_xml(xml_content, config.CATALOG_ID, page_key)
        logger.debug("XML content for page %s saved.", page_key)

        page_texts = parse_search_xml(xml_content)
        product_links = [link for link in page_data.get("links", []) if link.get("url") and link.get("url").startswith('http')]
        logger.info("Found %s product links on page %s. Associating text...", len(product_links), page_key)

        for i, link in enumerate(product_links):
            rect = link.get('rect')
            url = link.get('url')

            if not rect or not (isinstance(rect, list) and len(rect) == 4) or not url:
                logger.warning("Skipping product link due to missing/invalid rect or url: %s", link)
                continue

            product_key = f"{page_key}_prod_{i+1}"
            associated_text = find_text_near_rect(page_texts, rect)

            # Extracting name, prices, skus
            url_parts = url.split('/')
            name = url_parts[-1].replace('-', ' ').title() if url_parts[-1] else "Unknown Product"
            prices = re.findall(r'\$[\d,]+\.?\d*', associated_text)
            skus = re.findall(r'(?i)(?:SKU|Item|Model)[\s:#]*([A-Z0-9\-]+)', associated_text)

            product_details = ProductDetailsAspect(
                catalog_id=config.CATALOG_ID,
                page_key=page_key,
                product_key=product_key,
                product_url=url,
                product_name=name,
                prices_found=list(set(prices)),
                skus_found=list(set(skus)),
                full_text=re.sub(r'\s+', ' ', associated_text).strip()
            )
            file_manager.save_product_details(product_details)
            logger.info("SUCCESS: Extracted and saved data for [bold green]%s[/bold green] (URL: %s)", product_key, url)
            logger.debug("Product Details: %s", json.dumps(product_details.dict()))

    logger.info("--- STEP 2 COMPLETE ---")