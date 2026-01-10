"""KMU Knowledge Assistant - Utils Module"""

from app.utils.scraper import web_scraper, WebScraper, ScrapingJob, SWISS_SOURCES
from app.utils.file_handlers import (
    is_supported_file,
    get_file_category,
    save_uploaded_file,
    format_file_size,
    get_storage_stats
)

__all__ = [
    "web_scraper",
    "WebScraper",
    "ScrapingJob",
    "SWISS_SOURCES",
    "is_supported_file",
    "get_file_category",
    "save_uploaded_file",
    "format_file_size",
    "get_storage_stats"
]
