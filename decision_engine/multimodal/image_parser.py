"""
Image Parser Module

Handles extraction of text and metadata from images using OCR (Optical Character Recognition).
Uses pytesseract (free, open-source) and PIL for image preprocessing.

Example Use Cases:
    - Extract text from screenshots of business metrics
    - Parse charts/diagrams with text labels
    - Read handwritten notes (limited accuracy)
    - Extract data from scanned documents
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Union
from io import BytesIO

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("PIL not installed. Install with: uv add pillow")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("pytesseract not installed. Install with: uv add pytesseract")

from .config import (
    SUPPORTED_IMAGE_FORMATS,
    OCR_CONFIG,
    IMAGE_PREPROCESSING,
    MAX_FILE_SIZE_MB,
    EXTRACTION_CONFIG,
)

logger = logging.getLogger(__name__)


class ImageParser:
    """
    Parses images to extract text using OCR.
    
    Attributes:
        ocr_lang (str): Language for OCR (default: 'eng')
        config (str): Tesseract configuration string
    """
    
    def __init__(self, ocr_lang: str = "eng", custom_config: Optional[str] = None):
        """
        Initialize ImageParser.
        
        Args:
            ocr_lang (str): Language code for OCR (e.g., 'eng', 'spa', 'fra')
            custom_config (str, optional): Custom Tesseract config string
        """
        if not PIL_AVAILABLE:
            raise ImportError("PIL/Pillow is required. Install: uv add pillow")
        if not TESSERACT_AVAILABLE:
            raise ImportError("pytesseract is required. Install: uv add pytesseract")
        
        self.ocr_lang = ocr_lang
        self.config = custom_config or OCR_CONFIG["config"]
        logger.info(f"ImageParser initialized with language: {ocr_lang}")
    
    def _validate_image_file(self, file_path: Path) -> bool:
        """
        Validate image file format and size.
        
        Args:
            file_path (Path): Path to image file
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check file extension
        if file_path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
            logger.error(f"Unsupported image format: {file_path.suffix}")
            return False
        
        # Check file size (in MB)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.error(f"File too large: {file_size_mb:.2f}MB (max: {MAX_FILE_SIZE_MB}MB)")
            return False
        
        logger.debug(f"Image file validated: {file_path.name} ({file_size_mb:.2f}MB)")
        return True
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy.
        
        Steps:
            1. Resize if too large (performance optimization)
            2. Convert to grayscale (improves OCR)
            3. Enhance contrast (optional, improves text clarity)
        
        Args:
            image (PIL.Image): Input image
            
        Returns:
            PIL.Image: Preprocessed image
        """
        # Resize if necessary (performance on free tier)
        max_width = IMAGE_PREPROCESSING["resize_max_width"]
        max_height = IMAGE_PREPROCESSING["resize_max_height"]
        
        if image.width > max_width or image.height > max_height:
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            logger.debug(f"Image resized to: {image.width}x{image.height}")
        
        # Convert to RGB if not already (some formats need this)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        
        # Convert to grayscale for better OCR (optional but recommended)
        # Uncomment below to enable grayscale conversion
        # image = image.convert('L')
        
        return image
    
    def extract_text_from_file(self, file_path: Union[str, Path]) -> Dict[str, Union[str, bool]]:
        """
        Extract text from an image file.
        
        Args:
            file_path (str | Path): Path to image file
            
        Returns:
            dict: {
                'success': bool,
                'text': str (extracted text),
                'error': str (error message if failed),
                'metadata': dict (image dimensions, format, etc.)
            }
        """
        try:
            file_path = Path(file_path)
            
            # Validate file
            if not file_path.exists():
                return {"success": False, "text": "", "error": "File not found"}
            
            if not self._validate_image_file(file_path):
                return {"success": False, "text": "", "error": "Invalid image file"}
            
            # Open and preprocess image
            logger.info(f"Processing image: {file_path.name}")
            image = Image.open(file_path)
            image = self._preprocess_image(image)
            
            # Extract text using OCR
            extracted_text = pytesseract.image_to_string(
                image,
                lang=self.ocr_lang,
                config=self.config
            )
            
            # Clean extracted text
            extracted_text = extracted_text.strip()
            
            # Validate text length
            if len(extracted_text) < EXTRACTION_CONFIG["min_text_length"]:
                logger.warning(f"Extracted text too short: {len(extracted_text)} chars")
                return {
                    "success": True,
                    "text": extracted_text,
                    "error": "No significant text found in image",
                    "metadata": self._get_image_metadata(image, file_path)
                }
            
            # Truncate if too long (prevent token overflow)
            if len(extracted_text) > EXTRACTION_CONFIG["max_text_length"]:
                logger.warning(f"Truncating text from {len(extracted_text)} to {EXTRACTION_CONFIG['max_text_length']} chars")
                extracted_text = extracted_text[:EXTRACTION_CONFIG["max_text_length"]] + "... [truncated]"
            
            logger.info(f"Successfully extracted {len(extracted_text)} characters from {file_path.name}")
            
            return {
                "success": True,
                "text": extracted_text,
                "error": None,
                "metadata": self._get_image_metadata(image, file_path)
            }
        
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}", exc_info=True)
            return {
                "success": False,
                "text": "",
                "error": f"OCR failed: {str(e)}",
                "metadata": {}
            }
    
    def extract_text_from_bytes(self, image_bytes: bytes, filename: str = "unknown.png") -> Dict[str, Union[str, bool]]:
        """
        Extract text from image bytes (useful for uploaded files).
        
        Args:
            image_bytes (bytes): Image data as bytes
            filename (str): Original filename (for logging/metadata)
            
        Returns:
            dict: Same format as extract_text_from_file()
        """
        try:
            # Check size
            size_mb = len(image_bytes) / (1024 * 1024)
            if size_mb > MAX_FILE_SIZE_MB:
                return {
                    "success": False,
                    "text": "",
                    "error": f"File too large: {size_mb:.2f}MB (max: {MAX_FILE_SIZE_MB}MB)"
                }
            
            # Open image from bytes
            logger.info(f"Processing image bytes: {filename}")
            image = Image.open(BytesIO(image_bytes))
            image = self._preprocess_image(image)
            
            # Extract text
            extracted_text = pytesseract.image_to_string(
                image,
                lang=self.ocr_lang,
                config=self.config
            ).strip()
            
            # Validate and truncate
            if len(extracted_text) < EXTRACTION_CONFIG["min_text_length"]:
                return {
                    "success": True,
                    "text": extracted_text,
                    "error": "No significant text found in image",
                    "metadata": self._get_image_metadata(image, filename)
                }
            
            if len(extracted_text) > EXTRACTION_CONFIG["max_text_length"]:
                extracted_text = extracted_text[:EXTRACTION_CONFIG["max_text_length"]] + "... [truncated]"
            
            logger.info(f"Successfully extracted {len(extracted_text)} characters from bytes")
            
            return {
                "success": True,
                "text": extracted_text,
                "error": None,
                "metadata": self._get_image_metadata(image, filename)
            }
        
        except Exception as e:
            logger.error(f"Error extracting text from bytes: {e}", exc_info=True)
            return {
                "success": False,
                "text": "",
                "error": f"OCR failed: {str(e)}",
                "metadata": {}
            }
    
    def _get_image_metadata(self, image: Image.Image, source: Union[str, Path]) -> Dict[str, Union[str, int]]:
        """
        Extract metadata from image.
        
        Args:
            image (PIL.Image): Image object
            source (str | Path): Source filename/path
            
        Returns:
            dict: Metadata (format, dimensions, mode)
        """
        return {
            "filename": str(Path(source).name) if isinstance(source, (str, Path)) else source,
            "format": image.format or "Unknown",
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "size_pixels": image.width * image.height
        }
