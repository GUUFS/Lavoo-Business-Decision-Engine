# config/__init__.py
"""
Configuration module for the AI Business Analyst application.
Provides centralized configuration for logging, database, and other settings.
"""

from .logging import get_logger, is_cloud_environment, setup_logging

__all__ = ["setup_logging", "get_logger", "is_cloud_environment"]
