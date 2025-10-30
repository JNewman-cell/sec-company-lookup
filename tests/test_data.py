"""
Shared test data for sec-company-lookup tests.

This module provides consistent test data structures that match the actual
SEC API format and the expected memory cache structure.
"""

from typing import Dict, Any

# Sample test data mimicking SEC API structure (company_tickers.json format)
SAMPLE_SEC_DATA: Dict[str, Dict[str, str]] = {
    "0": {"cik_str": "0000320193", "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": "0000789019", "ticker": "MSFT", "title": "Microsoft Corporation"},
    "2": {"cik_str": "0001652044", "ticker": "GOOGL", "title": "Alphabet Inc."},
    "3": {"cik_str": "0001018724", "ticker": "AMZN", "title": "Amazon.com, Inc."},
    "4": {"cik_str": "0000320193", "ticker": "AAPL-WT", "title": "Apple Inc."},
    "5": {"cik_str": "0001652044", "ticker": "GOOG", "title": "Alphabet Inc."},
}

# Sample memory cache structure that matches the actual cache structure used by the application
SAMPLE_MEMORY_CACHE: Dict[str, Any] = {
    "companies": {
        "0": {"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."},
        "1": {"cik": 789019, "ticker": "MSFT", "name": "Microsoft Corporation"},
        "2": {"cik": 1652044, "ticker": "GOOGL", "name": "Alphabet Inc."},
        "3": {"cik": 1018724, "ticker": "AMZN", "name": "Amazon.com, Inc."},
        "4": {"cik": 320193, "ticker": "AAPL-WT", "name": "Apple Inc."},
        "5": {"cik": 1652044, "ticker": "GOOG", "name": "Alphabet Inc."},
    },
    "by_ticker": {
        "AAPL": "0",
        "MSFT": "1",
        "GOOGL": "2",
        "AMZN": "3",
        "AAPL-WT": "4",
        "GOOG": "5",
    },
    "by_cik": {
        320193: ["0", "4"],  # AAPL and AAPL-WT share same CIK
        789019: ["1"],  # MSFT
        1652044: ["2", "5"],  # GOOGL and GOOG share same CIK
        1018724: ["3"],  # AMZN
    },
    "by_name": {
        "apple inc.": ["0", "4"],  # Both AAPL entries
        "microsoft corporation": ["1"],
        "alphabet inc.": ["2", "5"],  # Both Google entries
        "amazon.com, inc.": ["3"],
    },
}

__all__ = [
    "SAMPLE_SEC_DATA",
    "SAMPLE_MEMORY_CACHE",
]
