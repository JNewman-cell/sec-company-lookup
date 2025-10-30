"""
Test configuration and fixtures for sec-company-lookup.

This module provides shared test utilities and configuration.
"""

# Import shared test data for easy access
from .test_data import SAMPLE_SEC_DATA, SAMPLE_MEMORY_CACHE

__all__ = [
    "SAMPLE_SEC_DATA",
    "SAMPLE_MEMORY_CACHE",
]
