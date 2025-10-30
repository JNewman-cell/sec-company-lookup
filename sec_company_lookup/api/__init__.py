"""
API module for sec-company-lookup.
"""

from .api import (
    get_company,
    get_companies_by_tickers,
    get_companies_by_ciks,
    get_companies_by_names,
    search_companies,
    search_companies_by_ticker,
    search_companies_by_company_name,
    update_data,
    clear_cache,
    get_cache_info,
)

__all__ = [
    "get_company",
    "get_companies_by_tickers",
    "get_companies_by_ciks",
    "get_companies_by_names",
    "search_companies",
    "search_companies_by_ticker",
    "search_companies_by_company_name",
    "update_data",
    "clear_cache",
    "get_cache_info",
]
