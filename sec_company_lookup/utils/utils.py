"""
Utility functions for sec-company-lookup package.

This module contains utility functions for data fetching, cache management,
and common operations used across the sec-company-lookup package.
"""

import json
import requests
import time
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Constants
SEC_DATA_URL = "https://www.sec.gov/files/company_tickers.json"
CACHE_DIR = Path.home() / ".sec_company_lookup"
DATA_FILE = CACHE_DIR / "company_data.json"
CACHE_EXPIRY_HOURS = 24  # Refresh data every 24 hours


def ensure_cache_dir() -> None:
    """Ensure the cache directory exists."""
    CACHE_DIR.mkdir(exist_ok=True)


def download_sec_data() -> Dict[str, Any]:
    """Download the latest SEC company data."""
    logger.info("Downloading SEC company data...")

    # Get user agent using the new configuration system
    from ..config import get_user_agent
    
    try:
        user_agent = get_user_agent()
    except ValueError as e:
        raise ValueError(str(e)) from e

    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
        "Host": "www.sec.gov",
    }

    try:
        response = requests.get(SEC_DATA_URL, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()  # type: ignore[no-any-return]

        # Save raw data to file
        ensure_cache_dir()
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)

        logger.info(f"Downloaded data for {len(data)} companies")
        return data  # type: ignore[no-any-return]

    except requests.RequestException as e:
        logger.error(f"Failed to download SEC data: {e}")
        # Try to load from cache if available
        if DATA_FILE.exists():
            logger.info("Loading from cached file...")
            with open(DATA_FILE, "r") as f:
                return json.load(f)  # type: ignore[no-any-return]
        raise


def is_cache_expired(last_update: Optional[float]) -> bool:
    """Check if the cache is expired."""
    if not last_update:
        return True

    age_hours = (time.time() - last_update) / 3600
    return age_hours > CACHE_EXPIRY_HOURS


def load_from_cache() -> Tuple[Optional[Dict[str, Any]], float]:
    """
    Load data from cache if available and not expired.

    Returns:
        Tuple of (data, last_update_timestamp) or (None, 0) if no valid cache
    """
    # Try to load from file cache first (faster than DB)
    if DATA_FILE.exists():
        try:
            # Check file modification time for expiry
            file_age_hours = (time.time() - DATA_FILE.stat().st_mtime) / 3600
            if file_age_hours <= CACHE_EXPIRY_HOURS:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)  # type: ignore[no-any-return]
                last_update = DATA_FILE.stat().st_mtime
                logger.info("Loaded data from file cache")
                return data, last_update
        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.warning(f"Failed to load from cache file: {e}")

    return None, 0


def normalize_cik(cik_raw: Any) -> Optional[int]:
    """
    Normalize CIK to integer format.

    Args:
        cik_raw: CIK value (can be string or int)

    Returns:
        int: Normalized CIK as integer, or None if invalid
    """
    if isinstance(cik_raw, int):
        return cik_raw
    elif isinstance(cik_raw, str):
        cik = cik_raw.lstrip("0")
        return int(cik) if cik.isdigit() else None
    else:
        return None


def clear_cache_files() -> None:
    """Remove cache files from disk."""
    from ..db.db import DB_PATH

    if DATA_FILE.exists():
        DATA_FILE.unlink()
    if DB_PATH.exists():
        DB_PATH.unlink()

    logger.info("Cache files cleared")
