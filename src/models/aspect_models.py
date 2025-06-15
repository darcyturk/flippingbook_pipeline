# src/models/aspect_models.py

from dataclasses import dataclass
from typing import List

@dataclass
class ProductDetailsAspect:
    """
    This class is the blueprint for our final output. It represents all the
    structured data we want to extract for a single product.
    """
    catalog_id: str
    page_key: str
    product_key: str
    product_url: str
    product_name: str
    prices_found: List[str]
    skus_found: List[str]
    full_text: str

