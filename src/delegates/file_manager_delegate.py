# src/delegates/file_manager_delegate.py
import json
import re
import logging
from pathlib import Path
from typing import List, Dict
from PIL import Image
from ..models import ProductDetailsAspect

logger = logging.getLogger(__name__)

class FileManagerDelegate:
    """Handles all file system interactions for the pipeline."""
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.pager_path = base_path / "1_pager"
        self.pages_path = base_path / "2_pages"
        self.images_path = base_path / "3_images"
        self.products_path = base_path / "4_products"
        for p in [self.pager_path, self.pages_path, self.images_path, self.products_path]:
            p.mkdir(parents=True, exist_ok=True)
        logger.info("File manager initialized. Data will be stored in subdirectories of: %s", base_path)
    def save_ocr_task_list(self, tasks: List[Dict]) -> Path:
        file_path = self.base_path / "ocr_task_list.json"
        with file_path.open("w", encoding="utf-8") as f: json.dump(tasks, f, indent=2)
        logger.info("Saved OCR Task List manifest: %s", file_path.name)
        return file_path
    def read_ocr_task_list(self) -> List[Dict]:
        file_path = self.base_path / "ocr_task_list.json"
        if not file_path.exists(): return []
        with file_path.open("r", encoding="utf-8") as f: return json.load(f)
    def save_pager_json(self, catalog_json: Dict, catalog_id: str) -> Path:
        file_path = self.pager_path / f"pager_{catalog_id}.json"
        with file_path.open("w", encoding="utf-8") as f: json.dump(catalog_json, f, indent=2)
        logger.info("Saved Pager JSON: %s", file_path.name)
        return file_path
    def save_page_layout(self, page_data: Dict, catalog_id: str, page_key: str):
        file_path = self.pages_path / f"layout_{catalog_id}_{page_key}.json"
        with file_path.open("w", encoding="utf-8") as f: json.dump(page_data, f, indent=2)
    def save_product_image(self, image: Image.Image, catalog_id: str, page_key: str, product_key: str) -> Path:
        safe_product_key = re.sub(r'[^a-zA-Z0-9_-]', '_', product_key)
        image_dir = self.images_path / catalog_id / page_key
        image_dir.mkdir(parents=True, exist_ok=True)
        file_path = image_dir / f"{safe_product_key}.jpeg"
        image.convert("RGB").save(file_path, "JPEG")
        return file_path
    def save_product_details(self, product_details: ProductDetailsAspect):
        safe_product_key = re.sub(r'[^a-zA-Z0-9_-]', '_', product_details.product_key)
        details_dir = self.products_path / product_details.catalog_id / product_details.page_key
        details_dir.mkdir(parents=True, exist_ok=True)
        file_path = details_dir / f"{safe_product_key}.json"
        with file_path.open("w", encoding="utf-8") as f: json.dump(product_details.__dict__, f, indent=2, ensure_ascii=False)

