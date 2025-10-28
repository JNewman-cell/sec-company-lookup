"""
secmap - Fast, cached SEC company data lookups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A lightweight Python package for instant lookups between stock tickers,
CIK identifiers, and company names using the official SEC company_tickers.json dataset.

Basic usage:
    >>> from secmap import get_company, update_data
    >>> update_data()  # Download latest SEC data
    >>> company = get_company("AAPL")
    >>> print(company)
    {'cik': 320193, 'ticker': 'AAPL', 'name': 'Apple Inc.'}
"""

from .secmap import (
    get_company,
    get_company_by_ticker,
    get_company_by_cik,
    get_company_by_name,
    search_companies,
    search_companies_by_company_name,
    get_companies_by_ciks,
    get_companies_by_company_names,
    get_companies_by_sector_search,
    update_data,
    clear_cache,
    get_cache_info,
)

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

__all__ = [
    "get_company",
    "get_company_by_ticker",
    "get_company_by_cik",
    "get_company_by_name",
    "search_companies",
    "search_companies_by_company_name",
    "get_companies_by_ciks",
    "get_companies_by_company_names",
    "get_companies_by_sector_search",
    "update_data",
    "clear_cache",
    "get_cache_info",
]
