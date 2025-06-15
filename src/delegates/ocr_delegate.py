# src/delegates/ocr_delegate.py
import pytesseract
import re
import logging
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
from typing import List, Dict
from ..models import ProductDetailsAspect

logger = logging.getLogger(__name__)

class OCRDelegate:
    """Handles all OCR and text analysis tasks."""
    def __init__(self, primary_config: str, known_brands: List[str]):
        self.tesseract_config = primary_config
        self.brand_patterns = [r'\b(?:' + '|'.join(known_brands) + r')\b']
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        gray = image.convert('L')
        contrast = ImageEnhance.Contrast(gray).enhance(1.5)
        return contrast.filter(ImageFilter.SHARPEN)
    def _analyze_text(self, text: str, ids: Dict) -> ProductDetailsAspect:
        prices = re.findall(r'\$[\d,]+\.?\d*', text)
        skus = re.findall(r'(?i)(?:SKU|Item|Model)[\s:#]*([A-Z0-9\-]+)', text)
        url_parts = ids['product_url'].split('/')
        name = url_parts[-1].replace('-', ' ').title() if url_parts[-1] else "Unknown Product"
        return ProductDetailsAspect(
            catalog_id=ids['catalog_id'],
            page_key=ids['page_key'],
            product_key=ids['product_key'],
            product_url=ids['product_url'],
            product_name=name,
            prices_found=list(set(prices)),
            skus_found=list(set(skus)),
            full_text=re.sub(r'\s+', ' ', text).strip()
        )
    def extract_details_from_image(self, image: Image.Image, identifiers: Dict) -> ProductDetailsAspect:
        try:
            processed_image = self._preprocess_image(image)
            text = pytesseract.image_to_string(processed_image, config=self.tesseract_config)
            return self._analyze_text(text, identifiers)
        except Exception as e:
            logger.error("OCR extraction failed for product %s: %s", identifiers['product_key'], e)
            return None
