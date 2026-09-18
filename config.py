"""
System Configuration Module
Handles project directory paths, logging configuration, and application metadata.
"""

import logging
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
LOGS_DIR = BASE_DIR / "logs"
SCHEMA_PATH = BASE_DIR / "schema.sql"
DEFAULT_DB_PATH = DATA_DIR / "engineering_project_qa.db"
LOG_FILE_PATH = LOGS_DIR / "app.log"

# Ensure essential runtime directories exist
for directory in (DATA_DIR, EXPORTS_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Application Metadata
APP_TITLE = "Engineering Project Support & Quality Assurance Management System"
APP_SUBTITLE = "Academic Portfolio Project — Project Support, Traceability & QA Engine"
APP_VERSION = "1.0.0"


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """Configures file and console logging with consistent formatting."""
    logger = logging.getLogger("eng_qa_system")
    logger.setLevel(log_level)

    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s (%(module)s:%(lineno)d): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        try:
            file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not configure file logger at {LOG_FILE_PATH}: {e}")

        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


logger = setup_logging()
