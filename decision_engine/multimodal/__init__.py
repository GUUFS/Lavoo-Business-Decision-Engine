"""
Multimodal Analysis Module

This module provides functionality to parse and analyze images and documents
for the Business Decision Engine. It extracts text and context from various
file formats to enhance business problem analysis.

Future Feature: Will be integrated with the frontend decision engine page
to allow users to upload images/documents alongside text queries.

Supported Formats:
    - Images: PNG, JPG, JPEG, BMP, TIFF (via OCR or Grok Vision)
    - Documents: PDF, DOCX, TXT

Dependencies:
    - xai-sdk (Grok Vision and Grok LLM) - FREE TIER AVAILABLE
    - pytesseract (OCR for images - fallback) - FREE
    - pdf2image (PDF to image conversion) - FREE
    - PyPDF2 or pdfplumber (PDF text extraction) - FREE
    - python-docx (DOCX parsing) - FREE
    - Pillow/PIL (Image processing) - FREE
"""

from .handler import MultimodalHandler
from .image_parser import ImageParser
from .document_parser import DocumentParser

__all__ = ["MultimodalHandler", "ImageParser", "DocumentParser"]
