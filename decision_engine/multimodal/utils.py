"""
Utility Functions for Multimodal Analysis

Common helper functions used across image and document parsing modules.
"""

import logging
from pathlib import Path
from typing import Union, Optional

logger = logging.getLogger(__name__)


def validate_file_path(file_path: Union[str, Path]) -> Optional[Path]:
    """
    Validate and convert file path to Path object.
    
    Args:
        file_path (str | Path): Path to validate
        
    Returns:
        Path | None: Validated Path object or None if invalid
    """
    try:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File does not exist: {path}")
            return None
        if not path.is_file():
            logger.error(f"Path is not a file: {path}")
            return None
        return path
    except Exception as e:
        logger.error(f"Invalid file path: {e}")
        return None


def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path (Path): Path to file
        
    Returns:
        float: File size in MB
    """
    return file_path.stat().st_size / (1024 * 1024)


def truncate_text(text: str, max_length: int, suffix: str = "... [truncated]") -> str:
    """
    Truncate text to maximum length with suffix.
    
    Args:
        text (str): Text to truncate
        max_length (int): Maximum length
        suffix (str): Suffix to add if truncated
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def clean_extracted_text(text: str) -> str:
    """
    Clean extracted text (remove extra whitespace, normalize newlines).
    
    Args:
        text (str): Raw extracted text
        
    Returns:
        str: Cleaned text
    """
    # Remove excessive whitespace
    lines = [line.strip() for line in text.split("\n")]
    # Remove empty lines (but keep paragraph breaks)
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        if line:
            cleaned_lines.append(line)
            prev_empty = False
        elif not prev_empty:
            cleaned_lines.append("")  # Single empty line for paragraph break
            prev_empty = True
    
    return "\n".join(cleaned_lines).strip()


def estimate_token_count(text: str) -> int:
    """
    Rough estimate of token count (for Cohere API planning).
    
    Uses simple heuristic: ~4 chars per token (average for English).
    
    Args:
        text (str): Text to estimate
        
    Returns:
        int: Estimated token count
    """
    return len(text) // 4


def format_extraction_summary(result: dict) -> str:
    """
    Format extraction result into a human-readable summary.
    
    Args:
        result (dict): Extraction result from ImageParser or DocumentParser
        
    Returns:
        str: Formatted summary
    """
    if not result.get("success"):
        return f"❌ Extraction failed: {result.get('error', 'Unknown error')}"
    
    metadata = result.get("metadata", {})
    text_length = len(result.get("text", ""))
    
    summary_parts = ["✅ Extraction successful"]
    summary_parts.append(f"   - Characters extracted: {text_length:,}")
    
    if "filename" in metadata:
        summary_parts.append(f"   - File: {metadata['filename']}")
    
    if "page_count" in metadata:
        summary_parts.append(f"   - Pages: {metadata['page_count']}")
    
    if "parser" in metadata:
        summary_parts.append(f"   - Parser: {metadata['parser']}")
    
    if "width" in metadata and "height" in metadata:
        summary_parts.append(f"   - Dimensions: {metadata['width']}x{metadata['height']}px")
    
    return "\n".join(summary_parts)


def batch_process_results(results: list) -> dict:
    """
    Aggregate results from multiple file processing operations.
    
    Args:
        results (list): List of extraction results
        
    Returns:
        dict: {
            'total_files': int,
            'successful': int,
            'failed': int,
            'total_chars': int,
            'errors': list
        }
    """
    summary = {
        "total_files": len(results),
        "successful": 0,
        "failed": 0,
        "total_chars": 0,
        "errors": []
    }
    
    for result in results:
        if result.get("success"):
            summary["successful"] += 1
            summary["total_chars"] += len(result.get("text", ""))
        else:
            summary["failed"] += 1
            error_msg = result.get("error", "Unknown error")
            source = result.get("metadata", {}).get("filename", "unknown")
            summary["errors"].append(f"{source}: {error_msg}")
    
    return summary


# Export all utilities
__all__ = [
    "validate_file_path",
    "get_file_size_mb",
    "truncate_text",
    "clean_extracted_text",
    "estimate_token_count",
    "format_extraction_summary",
    "batch_process_results"
]
