"""
Configuration for Multimodal Analysis Module

Settings and constants for image/document parsing operations.
"""

from pathlib import Path
from typing import Set

# Base directory for multimodal operations
BASE_DIR = Path(__file__).parent

# Supported file formats
SUPPORTED_IMAGE_FORMATS: Set[str] = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
SUPPORTED_DOC_FORMATS: Set[str] = {".pdf", ".docx", ".txt"}

# OCR settings (Tesseract)
OCR_CONFIG = {
    "lang": "eng",  # Language for OCR (English by default)
    "config": "--psm 6",  # Page segmentation mode: Assume uniform block of text
}

# Image preprocessing settings
IMAGE_PREPROCESSING = {
    "resize_max_width": 2000,  # Max width for image processing (performance)
    "resize_max_height": 2000,  # Max height for image processing
    "dpi": 300,  # DPI for PDF to image conversion
}

# File size limits (in MB)
MAX_FILE_SIZE_MB = 10  # Max file size to prevent memory issues on free tier

# Extraction settings
EXTRACTION_CONFIG = {
    "min_text_length": 10,  # Minimum text length to consider valid
    "max_text_length": 50000,  # Maximum text length to prevent token overflow
}

# Logging
LOG_LEVEL = "INFO"
