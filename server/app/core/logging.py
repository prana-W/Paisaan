import logging
import sys
from app.core.config import get_settings


def setup_logging() -> None:
    """Configure application-wide logging with minimal, clean log output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )

    # Quieten noisy third-party libraries and DB engine
    noisy_loggers = [
        "httpx",
        "httpcore",
        "urllib3",
        "uvicorn.access",
        "uvicorn.error",
        "sqlalchemy",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "sqlalchemy.orm",
        "langchain",
        "langchain_core",
        "langchain_google_genai",
        "langgraph",
        "google",
        "google.api_core",
        "google.genai",
        "duckduckgo_search",
        "yfinance",
        "psycopg",
        "psycopg_pool",
    ]

    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Call this at module level in each file."""
    return logging.getLogger(name)
