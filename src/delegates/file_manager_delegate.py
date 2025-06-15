# src/delegates/file_manager_delegate.py
import json
import re
import logging
from pathlib import Path
from typing import Dict, Optional
from ..models import ProductDetailsAspect

logger = logging.getLogger(__name__)

class FileManagerDelegate:
    """Handles all file system interactions for the pipeline."""
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.pager_path = base_path / "1_pager_json"
        self.pages_layouts_path = base_path / "2_pages_layouts"
        self.search_xml_path = base_path / "2b_search_xml"
        self.products_path = base_path / "3_products"
        self.signed_params_path = base_path / "0_signed_params" # NEW: Directory for signed params

        for p in [self.pager_path, self.pages_layouts_path, self.search_xml_path, self.products_path, self.signed_params_path]: # NEW: Include signed_params_path
            p.mkdir(parents=True, exist_ok=True)
        logger.info("File manager initialized. Data will be stored in subdirectories of: %s", base_path)

    def save_extracted_json(self, publication_model: Dict, catalog_id: str) -> Path:
        """Saves the publication model extracted from the HTML to a JSON file."""
        file_path = self.pager_path / f"pager_{catalog_id}.json"
        try:
            logger.debug("Attempting to save Publication Model to JSON.")
            logger.debug("Model type: %s", type(publication_model))
            logger.debug("Model snippet (first 200 chars of string representation): %s", str(publication_model)[:200] + "...")

            with file_path.open("w", encoding="utf-8") as f:
                json.dump(publication_model, f, indent=2, ensure_ascii=False)
            logger.info("Saved extracted Publication Model to: %s", file_path.name)
            return file_path
        except TypeError as te:
            logger.error("TypeError during JSON dump (unserializable object?): %s", te)
            logger.error("Problematic model type: %s", type(publication_model))
            raise
        except Exception as e:
            logger.error("Failed to save Publication Model to %s: %s", file_path, e, exc_info=True)
            raise
    
    # NEW: Method to save signed parameters
    def save_signed_params(self, params: Dict[str, str], catalog_id: str) -> Path:
        """Saves the extracted CloudFront signed parameters to a JSON file."""
        file_path = self.signed_params_path / f"signed_params_{catalog_id}.json"
        try:
            logger.debug("Attempting to save CloudFront signed parameters to JSON.")
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(params, f, indent=2, ensure_ascii=False)
            logger.info("Saved CloudFront signed parameters to: %s", file_path.name)
            return file_path
        except Exception as e:
            logger.error("Failed to save CloudFront signed parameters to %s: %s", file_path, e, exc_info=True)
            raise

    # NEW: Method to load signed parameters
    def load_signed_params(self, catalog_id: str) -> Optional[Dict[str, str]]:
        """Loads CloudFront signed parameters from a JSON file."""
        file_path = self.signed_params_path / f"signed_params_{catalog_id}.json"
        if not file_path.exists():
            logger.warning("CloudFront signed parameters file not found at: %s", file_path)
            return None
        try:
            with file_path.open("r", encoding="utf-8") as f:
                params = json.load(f)
            logger.info("Loaded CloudFront signed parameters from: %s", file_path.name)
            return params
        except json.JSONDecodeError as e:
            logger.error("Error decoding CloudFront signed parameters from JSON file %s: %s", file_path, e)
            return None
        except Exception as e:
            logger.error("Error loading CloudFront signed parameters from %s: %s", file_path, e, exc_info=True)
            return None

    def save_search_xml(self, xml_content: str, catalog_id: str, page_key: str):
        """Saves the downloaded search.xml content to a file."""
        file_path = self.search_xml_path / f"search_{catalog_id}_{page_key}.xml"
        try:
            with file_path.open("w", encoding="utf-8") as f:
                f.write(xml_content)
            logger.info("Saved Search XML for page %s", page_key)
        except Exception as e:
            logger.error("Failed to save Search XML for page %s to %s: %s", page_key, file_path, e, exc_info=True)
            raise

    def save_product_details(self, product_details: ProductDetailsAspect):
        """Saves the final, structured JSON output for a single product."""
        safe_product_key = re.sub(r'[^a-zA-Z0-9_-]', '_', product_details.product_key)
        details_dir = self.products_path / product_details.catalog_id / product_details.page_key
        details_dir.mkdir(parents=True, exist_ok=True)
        file_path = details_dir / f"{safe_product_key}.json"
        try:
            json_data = product_details.dict()
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            logger.info("Saved product details for %s to %s", safe_product_key, file_path.name)
        except TypeError as te:
            logger.error("TypeError during product details JSON dump (unserializable object?): %s", te)
            logger.error("Problematic product_details type: %s", type(product_details))
            logger.error("Product Details Data (snippet): %s", str(product_details.dict())[:500] + "...")
            raise
        except Exception as e:
            logger.error("Failed to save product details for %s to %s: %s", safe_product_key, file_path, e, exc_info=True)
            raise