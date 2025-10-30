"""
API layer for sec-company-lookup.

This module provides the public API for company lookups, delegating to the
backend for data management and caching.
"""

from typing import Dict, List, Optional, Union, Any, Sequence
import logging

from ..types import (
    CompanyData,
    BatchLookupResponse,
    MultipleLookupResponse,
)
from ..sec_company_lookup import (
    get_company_by_ticker_single,
    get_company_by_cik_single,
    get_company_by_name_single,
    ensure_data_loaded,
    get_companies_by_tickers_batch,
    get_companies_by_ciks_batch,
    get_companies_by_names_batch,
    search_companies_impl,
    search_companies_by_company_name_impl,
    update_data_impl,
    clear_cache_impl,
    get_cache_info_impl,
)

logger = logging.getLogger(__name__)


def get_companies_by_tickers(
    ticker: Union[str, Sequence[str]]
) -> Union[Optional[CompanyData], Dict[str, BatchLookupResponse]]:
    """
    Look up company information by ticker symbol(s).
    
    Supports both single and batch lookups:
    - Single ticker: Uses memory cache with LRU (fast), returns CompanyData or None
    - Multiple tickers: Uses database (efficient for batches), returns structured responses

    Args:
        ticker: Single ticker string or sequence of ticker strings

    Returns:
        For single ticker: CompanyData or None
        For multiple tickers: Dict mapping each ticker to BatchLookupResponse
            {
                "success": bool,
                "data": CompanyData (only on success),
                "error": str (only on failure),
                "error_code": str (only on failure)  # "INVALID_INPUT" or "NOT_FOUND"
            }

    Examples:
        >>> # Single lookup
        >>> company = get_companies_by_tickers("AAPL")
        
        >>> # Batch lookup
        >>> companies = get_companies_by_tickers(["AAPL", "MSFT", "INVALID"])
        >>> # Returns: {
        >>> #   "AAPL": {"success": True, "data": {...}},
        >>> #   "MSFT": {"success": True, "data": {...}},
        >>> #   "INVALID": {"success": False, "error": "Ticker 'INVALID' not found", "error_code": "NOT_FOUND"}
        >>> # }
    """
    # Batch input - route directly to database
    if not isinstance(ticker, str):
        return get_companies_by_tickers_batch(ticker)
    
    # Single ticker lookup - use LRU cached function, unwrap structured response
    response = get_company_by_ticker_single(ticker)
    return response.get("data") if response["success"] else None


def get_companies_by_ciks(
    cik: Union[int, str, Sequence[Union[int, str]]]
) -> Union[List[CompanyData], Dict[Union[int, str], MultipleLookupResponse]]:
    """
    Look up company information by CIK identifier(s).
    
    Supports both single and batch lookups:
    - Single CIK: Uses memory cache with LRU (fast), returns list of CompanyData
    - Multiple CIKs: Uses database (efficient for batches), returns structured responses

    Args:
        cik: Single CIK (int or string) or sequence of CIKs

    Returns:
        For single CIK: List of CompanyData (CIKs can have multiple tickers)
        For multiple CIKs: Dict mapping each CIK to MultipleLookupResponse
            {
                "success": bool,
                "data": List[CompanyData] (only on success),
                "error": str (only on failure),
                "error_code": str (only on failure)  # "INVALID_INPUT" or "NOT_FOUND"
            }

    Examples:
        >>> # Single lookup
        >>> companies = get_companies_by_ciks(320193)
        
        >>> # Batch lookup
        >>> results = get_companies_by_ciks([320193, 789019, "invalid"])
        >>> # Returns: {
        >>> #   320193: {"success": True, "data": [{...}]},
        >>> #   789019: {"success": True, "data": [{...}]},
        >>> #   "invalid": {"success": False, "error": "Invalid CIK: 'invalid' could not be normalized", "error_code": "INVALID_INPUT"}
        >>> # }
    """
    # Batch input - route directly to database
    if not isinstance(cik, (int, str)):
        return get_companies_by_ciks_batch(cik)
    
    # Single CIK lookup - use LRU cached function, unwrap structured response
    response = get_company_by_cik_single(cik)
    return response.get("data", []) if response["success"] else []


def get_companies_by_names(
    name: Union[str, Sequence[str]], fuzzy: bool = False
) -> Union[Optional[CompanyData], Dict[str, BatchLookupResponse]]:
    """
    Look up company information by company name(s).
    
    Supports both single and batch lookups:
    - Single name: Uses memory cache (fast), returns CompanyData or None
    - Multiple names: Uses database (efficient for batches), returns structured responses

    Args:
        name: Single company name or sequence of company names
        fuzzy: If True, perform fuzzy matching

    Returns:
        For single name: CompanyData or None
        For multiple names: Dict mapping each name to BatchLookupResponse
            {
                "success": bool,
                "data": CompanyData (only on success),
                "error": str (only on failure),
                "error_code": str (only on failure)  # "INVALID_INPUT" or "NOT_FOUND"
            }

    Examples:
        >>> # Single lookup
        >>> company = get_companies_by_names("Apple Inc.")
        
        >>> # Batch lookup
        >>> results = get_companies_by_names(["Apple", "Microsoft", ""], fuzzy=True)
        >>> # Returns: {
        >>> #   "Apple": {"success": True, "data": {...}},
        >>> #   "Microsoft": {"success": True, "data": {...}},
        >>> #   "": {"success": False, "error": "Invalid name: empty or whitespace", "error_code": "INVALID_INPUT"}
        >>> # }
    """
    # Batch input - route directly to database
    if isinstance(name, (list, tuple)):
        return get_companies_by_names_batch(list(name), fuzzy)
    
    # Single name lookup - use memory cache, unwrap structured response
    response = get_company_by_name_single(str(name), fuzzy)
    return response.get("data") if response["success"] else None


def search_companies_by_ticker(
    ticker_query: str, limit: int = 10, fuzzy: bool = True
) -> List[CompanyData]:
    """
    Search for companies by ticker symbol with various matching options.

    Args:
        ticker_query: Ticker search query
        limit: Maximum number of results to return
        fuzzy: If True, perform fuzzy matching; if False, exact matching only

    Returns:
        List of matching company dictionaries
        
    Examples:
        >>> # Exact match
        >>> results = search_companies_by_ticker("AAPL", fuzzy=False)
        
        >>> # Fuzzy match - finds tickers containing the query
        >>> results = search_companies_by_ticker("AA", fuzzy=True, limit=5)
    """
    if not ticker_query or not ticker_query.strip():
        return []
    
    ensure_data_loaded()
    
    # Use the general search function which already searches tickers
    # This is efficient because it searches across both tickers and names
    return search_companies_impl(ticker_query, limit, fuzzy)


def get_company(identifier: Any) -> List[CompanyData]:
    """
    Smart lookup that tries to determine the type of identifier.

    Args:
        identifier (Union[str, int, None]): Ticker, CIK, or company name

    Returns:
        List of dicts containing cik, ticker, and name, or empty list if not found.
        For ticker lookups, list will contain at most one item.
        For CIK/name lookups, list may contain multiple items.
    """
    ensure_data_loaded()

    if identifier is None:
        return []

    # Handle integers as CIKs
    if isinstance(identifier, int):
        result = get_companies_by_ciks(identifier)
        return result  # type: ignore[return-value]

    # Must be str at this point - check if it's actually a string
    if not isinstance(identifier, str):
        return []

    # Check for empty or whitespace-only strings
    if not identifier.strip():
        return []

    identifier_stripped = identifier.strip()

    # Try CIK first if it's all digits (CIKs are numeric)
    if identifier_stripped.isdigit():
        cik_result = get_companies_by_ciks(identifier_stripped)
        if cik_result:  # type: ignore[truthy-bool]
            return cik_result  # type: ignore[return-value]

    # Try ticker second (common case, exact match)
    ticker_result = get_companies_by_tickers(identifier_stripped)
    if ticker_result:
        return [ticker_result]  # type: ignore[list-item]

    # Finally try company name with fuzzy matching
    name_result = get_companies_by_names(identifier_stripped, fuzzy=True)
    if name_result:
        return [name_result]  # type: ignore[list-item]
    return []


def search_companies(
    query: str, limit: int = 10, fuzzy: bool = True
) -> List[CompanyData]:
    """
    Search for companies by partial name or ticker match.

    Args:
        query (str): Search query
        limit (int): Maximum number of results to return
        fuzzy (bool): If True, perform fuzzy matching; if False, exact matching only

    Returns:
        List of matching company dictionaries.
    """
    return search_companies_impl(query, limit, fuzzy)


def search_companies_by_company_name(
    company_name_query: str, limit: int = 10, fuzzy: bool = True
) -> List[CompanyData]:
    """
    Search for companies by company name with various matching options.

    Args:
        company_name_query: Company name search query
        limit: Maximum number of results to return
        fuzzy: If True, perform fuzzy matching; if False, exact matching only

    Returns:
        List of matching company dictionaries
    """
    return search_companies_by_company_name_impl(company_name_query, limit, fuzzy)


def update_data() -> bool:
    """
    Download and cache the latest SEC company data.

    Returns:
        bool: True if data was successfully updated, False otherwise.
    """
    return update_data_impl()


def clear_cache() -> None:
    """Clear all cached data including database."""
    clear_cache_impl()


def get_cache_info() -> Dict[str, Any]:
    """
    Get information about the current cache status.

    Returns:
        Dict with cache statistics and status.
    """
    return get_cache_info_impl()
