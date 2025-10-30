"""
Core sec-company-lookup module for SEC company data lookups.

This module provides fast, cached lookups between stock tickers, CIK identifiers,
and company names using the official SEC company_tickers.json dataset.
"""

import sqlite3
from typing import Dict, List, Union, Any, Sequence, Set, cast
import time
import logging

from .types import (
    CompanyData,
    SECCompanyInfo,
    CacheStructure,
    SingleLookupResponse,
    BatchLookupResponse,
    MultipleLookupResponse,
)
from .utils import (
    download_sec_data,
    is_cache_expired,
    load_from_cache,
    normalize_cik,
    clear_cache_files,
)
from .db import (
    load_data_to_db,
    search_companies_db,
    get_companies_by_ciks_db,
    get_companies_by_company_names_db,
    get_companies_by_tickers_db,
    search_companies_by_company_name_db,
    get_db_stats,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global in-memory cache
_memory_cache: CacheStructure = {
    "companies": {},
    "by_ticker": {},
    "by_cik": {},
    "by_name": {},
}
_last_update: float = 0


def _load_data_to_memory(data: Dict[str, Any]) -> None:
    """Load company data into memory cache with optimized structure supporting multiple matches."""
    global _memory_cache, _last_update

    # Use a more memory-efficient structure
    # Store each company once and reference by ID
    companies: Dict[str, CompanyData] = {}  # id -> company_data
    ticker_index: Dict[str, str] = {}  # ticker -> id (one-to-one for tickers)
    cik_index: Dict[int, List[str]] = {}  # cik -> list of ids (one-to-many for CIKs)
    name_index: Dict[str, List[str]] = {}  # name -> list of ids (one-to-many for names)

    company_id_counter = 0
    for _, company_info in data.items():
        if isinstance(company_info, dict):
            # Type cast to handle the fact that we know the structure from SEC API
            sec_info = cast(SECCompanyInfo, company_info)
            cik_raw: str = sec_info.get("cik_str", "") or ""
            ticker_raw: str = sec_info.get("ticker", "") or ""
            ticker: str = ticker_raw.upper()
            title: str = sec_info.get("title", "") or ""

            cik_int = normalize_cik(cik_raw)

            if cik_int is not None and ticker and title:
                company_id = str(company_id_counter)
                company_data: CompanyData = {
                    "cik": cik_int,
                    "ticker": ticker,
                    "name": title,
                }

                companies[company_id] = company_data

                # Ticker index remains one-to-one (tickers should be unique)
                ticker_index[ticker] = company_id

                # CIK index supports multiple companies per CIK
                if cik_int not in cik_index:
                    cik_index[cik_int] = []
                cik_index[cik_int].append(company_id)

                # Name index supports multiple companies per name (case insensitive)
                name_lower = title.lower()
                if name_lower not in name_index:
                    name_index[name_lower] = []
                name_index[name_lower].append(company_id)

                company_id_counter += 1

    _memory_cache = {
        "companies": companies,
        "by_ticker": ticker_index,
        "by_cik": cik_index,
        "by_name": name_index,
    }

    _last_update = time.time()
    logger.info(f"Loaded {len(companies)} companies into optimized memory cache")

    # Log statistics about multiple matches
    multi_cik_count = sum(1 for ids in cik_index.values() if len(ids) > 1)
    multi_name_count = sum(1 for ids in name_index.values() if len(ids) > 1)
    logger.info(
        f"Found {multi_cik_count} CIKs with multiple companies, "
        f"{multi_name_count} names with multiple companies"
    )


def ensure_data_loaded() -> None:
    """Ensure data is loaded, updating if necessary. Public for API layer."""
    global _last_update

    if not _memory_cache or is_cache_expired(_last_update):
        cached_data, cached_timestamp = load_from_cache()
        if cached_data:
            _load_data_to_memory(cached_data)
            _last_update = cached_timestamp
        else:
            try:
                if not update_data_impl():
                    raise RuntimeError(
                        "Unable to load SEC company data. Please check your internet connection."
                    )
            except ValueError:
                # Re-raise configuration errors (like missing User-Agent)
                raise


def update_data_impl() -> bool:
    """
    Backend implementation: Download and cache the latest SEC company data.

    Returns:
        bool: True if data was successfully updated, False otherwise.
    """
    try:
        data = download_sec_data()
        _load_data_to_memory(data)
        load_data_to_db(data)  # Database for search operations

        return True
    except ValueError as e:
        # Re-raise configuration errors (like missing User-Agent) immediately
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to update data: {e}")
        return False


def get_company_by_ticker_single(ticker: str) -> SingleLookupResponse:
    """Internal: Single ticker lookup. Returns structured response."""
    if not ticker or not ticker.strip():
        return {
            "success": False,
            "error": "Invalid ticker: empty or whitespace",
            "error_code": "INVALID_INPUT",
        }

    ensure_data_loaded()
    company_id = _memory_cache["by_ticker"].get(
        ticker.strip().upper()
    )  # type: ignore[attr-defined]
    if company_id is not None:
        return {
            "success": True,
            "data": _memory_cache["companies"][company_id],  # type: ignore[typeddict-item]
        }
    return {
        "success": False,
        "error": f"Ticker '{ticker}' not found",
        "error_code": "NOT_FOUND",
    }


def get_companies_by_tickers_batch(
    tickers: Sequence[str],
) -> Dict[str, BatchLookupResponse]:
    """
    Backend implementation: Batch ticker lookup.

    Args:
        tickers: Sequence of ticker strings

    Returns:
        Dict mapping each ticker to a structured response with success/data/error
    """
    if not tickers:
        return {}

    ensure_data_loaded()

    # Normalize tickers and track invalid inputs
    ticker_map = {t.strip().upper(): t for t in tickers if t and t.strip()}
    normalized_tickers = list(ticker_map.keys())

    # Handle empty/invalid tickers
    results: Dict[str, BatchLookupResponse] = {}
    for t in tickers:
        if not t or not t.strip():
            results[t] = {
                "success": False,
                "error": "Invalid ticker: empty or whitespace",
                "error_code": "INVALID_INPUT",
            }

    # Use database for batch operations
    try:
        db_results = get_companies_by_tickers_db(normalized_tickers)
        # Map back to original ticker format with structured responses
        for ticker_upper, companies in db_results.items():
            original_ticker = ticker_map[ticker_upper]
            if companies:
                results[original_ticker] = {
                    "success": True,
                    "data": cast(CompanyData, companies[0]),
                }
            else:
                results[original_ticker] = {
                    "success": False,
                    "error": f"Ticker '{original_ticker}' not found",
                    "error_code": "NOT_FOUND",
                }
    except (sqlite3.Error, Exception) as e:
        logger.warning(f"Database ticker lookup failed: {e}")
        # Fallback to individual memory lookups
        for ticker_upper in normalized_tickers:
            original_ticker = ticker_map[ticker_upper]
            single_response = get_company_by_ticker_single(ticker_upper)
            results[original_ticker] = cast(BatchLookupResponse, single_response)

    return results


def get_company_by_cik_single(cik: Union[int, str]) -> MultipleLookupResponse:
    """Internal: Single CIK lookup. Returns structured response."""
    cik_int = normalize_cik(cik)
    if cik_int is None:
        return {
            "success": False,
            "error": f"Invalid CIK: '{cik}' could not be normalized",
            "error_code": "INVALID_INPUT",
        }

    ensure_data_loaded()
    company_ids = _memory_cache["by_cik"].get(cik_int, [])  # type: ignore[attr-defined]
    company_list: List[CompanyData] = [
        _memory_cache["companies"][company_id] for company_id in company_ids
    ]  # type: ignore[misc]

    if company_list:
        return {"success": True, "data": company_list}
    return {
        "success": False,
        "error": f"CIK '{cik}' not found",
        "error_code": "NOT_FOUND",
    }


def get_companies_by_ciks_batch(
    ciks: Sequence[Union[int, str]],
) -> Dict[Union[int, str], MultipleLookupResponse]:
    """
    Backend implementation: Batch CIK lookup.

    Args:
        ciks: Sequence of CIK identifiers

    Returns:
        Dict mapping each CIK to a structured response with success/data/error
    """
    if not ciks:
        return {}

    ensure_data_loaded()

    # Normalize CIKs
    normalized_ciks: List[int] = []
    cik_map: Dict[int, Union[int, str]] = {}
    invalid_ciks: List[Union[int, str]] = []

    for c in ciks:
        cik_int = normalize_cik(c)
        if cik_int is not None:
            normalized_ciks.append(cik_int)
            cik_map[cik_int] = c
        else:
            invalid_ciks.append(c)

    # Initialize results with errors for invalid CIKs
    results: Dict[Union[int, str], MultipleLookupResponse] = {}
    for c in invalid_ciks:
        results[c] = {
            "success": False,
            "error": f"Invalid CIK: '{c}' could not be normalized",
            "error_code": "INVALID_INPUT",
        }

    # Use database for batch operations
    try:
        db_results = get_companies_by_ciks_db(normalized_ciks)
        # Map back to original CIK format with structured responses
        for cik_int, companies in db_results.items():
            original_cik = cik_map[cik_int]
            company_list = [cast(CompanyData, c) for c in companies]
            if company_list:
                results[original_cik] = {"success": True, "data": company_list}
            else:
                results[original_cik] = {
                    "success": False,
                    "error": f"CIK '{original_cik}' not found",
                    "error_code": "NOT_FOUND",
                }

        # Ensure all valid CIKs are in results (even if not in db_results)
        for original_cik in cik_map.values():
            if original_cik not in results:
                results[original_cik] = {
                    "success": False,
                    "error": f"CIK '{original_cik}' not found",
                    "error_code": "NOT_FOUND",
                }

        return results
    except (sqlite3.Error, Exception) as e:
        logger.warning(f"Database CIK lookup failed: {e}")
        # Fallback to individual memory lookups
        for cik_int in normalized_ciks:
            original_cik = cik_map[cik_int]
            single_response = get_company_by_cik_single(cik_map[cik_int])
            results[original_cik] = single_response
        return results


def get_company_by_name_single(name: str, fuzzy: bool = False) -> SingleLookupResponse:
    """Internal: Single name lookup from memory cache. Returns single best match."""
    if not name or not name.strip():
        return {
            "success": False,
            "error": "Invalid name: empty or whitespace",
            "error_code": "INVALID_INPUT",
        }

    ensure_data_loaded()
    name_stripped = name.strip()
    name_lower = name_stripped.lower()

    # Try exact match first
    company_ids = _memory_cache["by_name"].get(name_lower, [])  # type: ignore[attr-defined]
    if len(company_ids) == 1:
        # Exact match found with single result
        return {
            "success": True,
            "data": _memory_cache["companies"][company_ids[0]],  # type: ignore[index]
        }
    elif len(company_ids) > 1:
        # Multiple exact matches - return first one
        return {
            "success": True,
            "data": _memory_cache["companies"][company_ids[0]],  # type: ignore[index]
        }

    # No exact match - progressively shorten name from the end until we find exactly one result
    if fuzzy:
        words = name_stripped.split()

        while len(words) > 0:
            # Try current shortened name
            shortened = " ".join(words).lower()
            matching_companies: List[CompanyData] = []

            for cached_name, comp_ids in _memory_cache["by_name"].items():  # type: ignore[attr-defined]
                if shortened in cached_name:
                    for comp_id in comp_ids:
                        matching_companies.append(_memory_cache["companies"][comp_id])  # type: ignore[index]

            # If we found exactly one result, return it
            if len(matching_companies) == 1:
                return {"success": True, "data": matching_companies[0]}

            # If we found multiple results, quit - shortening further won't help
            if len(matching_companies) > 1:
                return {
                    "success": False,
                    "error": f"Company name '{name}' does not match any name",
                    "error_code": "NOT_FOUND",
                }

            # Remove last word and try again
            words.pop()

        # If we've exhausted all words without finding any match, return error
        return {
            "success": False,
            "error": f"Company name '{name}' does not match any name",
            "error_code": "NOT_FOUND",
        }

    return {
        "success": False,
        "error": f"Company name '{name}' not found",
        "error_code": "NOT_FOUND",
    }


def get_companies_by_names_batch(
    names: List[str], fuzzy: bool = False
) -> Dict[str, BatchLookupResponse]:
    """
    Backend implementation: Batch name lookup.

    Args:
        names: List of company names
        fuzzy: If True, perform fuzzy matching

    Returns:
        Dict mapping each name to a structured response with success/data/error
        Each name maps to a single best-matching company
    """
    if not names:
        return {}

    ensure_data_loaded()

    # Filter and track invalid names
    results: Dict[str, BatchLookupResponse] = {}
    valid_names: List[str] = []
    for name in names:
        if not name or not name.strip():
            results[name] = {
                "success": False,
                "error": "Invalid name: empty or whitespace",
                "error_code": "INVALID_INPUT",
            }
        else:
            valid_names.append(name)

    # Use database for batch operations
    try:
        db_results = get_companies_by_company_names_db(valid_names, fuzzy=fuzzy)
        for name, companies in db_results.items():
            company_list = [cast(CompanyData, c) for c in companies]
            if company_list:
                # Return only the first (best) match
                results[name] = {"success": True, "data": company_list[0]}
            else:
                results[name] = {
                    "success": False,
                    "error": f"Company name '{name}' not found",
                    "error_code": "NOT_FOUND",
                }

        # Ensure all valid names are in results
        for name in valid_names:
            if name not in results:
                results[name] = {
                    "success": False,
                    "error": f"Company name '{name}' not found",
                    "error_code": "NOT_FOUND",
                }

        return results
    except (sqlite3.Error, Exception) as e:
        logger.warning(f"Database name lookup failed: {e}")
        # Fallback to individual memory lookups
        for name in valid_names:
            results[name] = get_company_by_name_single(name, fuzzy)
        return results


def search_companies_impl(
    query: str, limit: int = 10, fuzzy: bool = True
) -> List[CompanyData]:
    """
    Backend implementation: Search for companies by partial name or ticker match.

    Args:
        query (str): Search query
        limit (int): Maximum number of results to return
        fuzzy (bool): If True, perform fuzzy matching; if False, exact matching only

    Returns:
        List of matching company dictionaries.
    """
    ensure_data_loaded()

    if not query or not query.strip():
        return []

    # First check in-memory cache for exact matches
    results: List[CompanyData] = []
    seen_ids: Set[str] = set()
    query_stripped = query.strip()
    query_upper = query_stripped.upper()
    query_lower = query_stripped.lower()

    # Check for exact ticker match first
    company_id = _memory_cache["by_ticker"].get(query_upper)  # type: ignore[attr-defined]
    if company_id is not None:
        results.append(_memory_cache["companies"][company_id])  # type: ignore[index]
        seen_ids.add(company_id)

    # Check for exact company name match
    company_ids = _memory_cache["by_name"].get(query_lower, [])  # type: ignore[attr-defined]
    for company_id in company_ids:
        if company_id not in seen_ids:
            results.append(_memory_cache["companies"][company_id])  # type: ignore[index]
            seen_ids.add(company_id)

    # If we have enough results from exact matches and fuzzy is disabled, return early
    if len(results) >= limit and not fuzzy:
        return results[:limit]

    # If we need more results or fuzzy is enabled, use database search
    if len(results) < limit:
        try:
            db_results = search_companies_db(query_stripped, limit, fuzzy)

            # Add database results, avoiding duplicates
            for db_result in db_results:
                if len(results) >= limit:
                    break
                # Check if this result is already in our results (by cik and ticker)
                is_duplicate = any(
                    r["cik"] == db_result["cik"] and r["ticker"] == db_result["ticker"]
                    for r in results
                )
                if not is_duplicate:
                    results.append(db_result)

        except sqlite3.Error as e:
            logger.warning(
                f"Database search failed, falling back to memory search: {e}"
            )
            # Fallback to in-memory search
            memory_results = _search_companies_memory(query_stripped, limit, fuzzy)

            # Add memory results, avoiding duplicates
            for mem_result in memory_results:
                if len(results) >= limit:
                    break
                is_duplicate = any(
                    r["cik"] == mem_result["cik"]
                    and r["ticker"] == mem_result["ticker"]
                    for r in results
                )
                if not is_duplicate:
                    results.append(mem_result)

    return results[:limit]


def _search_companies_memory(
    query: str, limit: int = 10, fuzzy: bool = True
) -> List[CompanyData]:
    """Fallback in-memory search for companies."""
    results: List[CompanyData] = []
    seen_ids: Set[str] = set()
    query_lower = query.lower()
    companies = _memory_cache["companies"]

    if fuzzy:
        # Fuzzy search: partial matching
        # Search by ticker first
        for ticker, company_id in _memory_cache["by_ticker"].items():  # type: ignore[attr-defined]
            if query_lower in ticker.lower() and company_id not in seen_ids:
                results.append(companies[company_id])  # type: ignore[index]
                seen_ids.add(company_id)
                if len(results) >= limit:
                    break

        # Search by company name if we need more results
        if len(results) < limit:
            for name, company_ids in _memory_cache["by_name"].items():  # type: ignore[attr-defined]
                for company_id in company_ids:
                    if company_id not in seen_ids and query_lower in name:
                        results.append(companies[company_id])  # type: ignore[index]
                        seen_ids.add(company_id)
                        if len(results) >= limit:
                            break
                if len(results) >= limit:
                    break
    else:
        # Exact matching only - already handled in the main function
        # This case should rarely be reached since exact matches are checked first
        pass

    return results


def search_companies_by_company_name_impl(
    company_name_query: str, limit: int = 10, fuzzy: bool = True
) -> List[CompanyData]:
    """
    Backend implementation: Search for companies by company name with various matching options.

    Args:
        company_name_query: Company name search query
        limit: Maximum number of results to return
        fuzzy: If True, perform fuzzy matching; if False, exact matching only

    Returns:
        List of matching company dictionaries
    """
    if not company_name_query or not company_name_query.strip():
        return []

    ensure_data_loaded()

    # First check in-memory cache for exact matches
    results: List[CompanyData] = []
    seen_ids: Set[str] = set()
    query_stripped = company_name_query.strip()
    query_lower = query_stripped.lower()

    # Check for exact company name match first
    company_ids = _memory_cache["by_name"].get(query_lower, [])  # type: ignore[attr-defined]
    for company_id in company_ids:
        results.append(_memory_cache["companies"][company_id])  # type: ignore[index]
        seen_ids.add(company_id)

    # If we have enough results from exact matches and fuzzy is disabled, return early
    if len(results) >= limit and not fuzzy:
        return results[:limit]

    # If we need more results or fuzzy is enabled, use database search
    if len(results) < limit:
        try:
            db_results = search_companies_by_company_name_db(
                query_stripped, limit, fuzzy
            )

            # Add database results, avoiding duplicates
            for db_result in db_results:
                if len(results) >= limit:
                    break
                # Check if this result is already in our results (by cik and ticker)
                is_duplicate = any(
                    r["cik"] == db_result["cik"] and r["ticker"] == db_result["ticker"]
                    for r in results
                )
                if not is_duplicate:
                    results.append(cast(CompanyData, db_result))

        except sqlite3.Error as e:
            logger.warning(
                f"Database company name search failed, falling back to memory search: {e}"
            )
            # Fallback to existing memory-based name search
            fallback_response = get_company_by_name_single(query_stripped, fuzzy=fuzzy)
            if fallback_response["success"] and "data" in fallback_response:
                fallback_result = fallback_response["data"]

                # Add fallback result if not duplicate and we haven't hit limit
                if len(results) < limit:
                    is_duplicate = any(
                        r["cik"] == fallback_result["cik"]
                        and r["ticker"] == fallback_result["ticker"]
                        for r in results
                    )
                    if not is_duplicate:
                        results.append(fallback_result)

    return results[:limit]


def clear_cache_impl() -> None:
    """Backend implementation: Clear all cached data including database."""
    global _memory_cache, _last_update

    _memory_cache = {
        "companies": {},
        "by_ticker": {},
        "by_cik": {},
        "by_name": {},
    }
    _last_update = 0

    # Remove cache files
    clear_cache_files()

    logger.info("Cache cleared")


def get_cache_info_impl() -> Dict[str, Any]:
    """
    Backend implementation: Get information about the current cache status.

    Returns:
        Dict with cache statistics and status.
    """
    ensure_data_loaded()

    # Get database stats
    db_stats = get_db_stats()

    return {
        "companies_cached": len(_memory_cache.get("companies", {})),  # type: ignore[arg-type]
        "last_update": _last_update,
        "cache_age_hours": (
            (time.time() - _last_update) / 3600 if _last_update else None
        ),
        "cache_expired": is_cache_expired(_last_update),
        "cache_dir": str(db_stats.get("cache_dir", "Unknown")),
        "data_file_exists": True,  # Will be checked in utils
        **db_stats,
        "memory_cache_structure": {
            "companies": len(_memory_cache.get("companies", {})),  # type: ignore[arg-type]
            "tickers_indexed": len(_memory_cache.get("by_ticker", {})),  # type: ignore[arg-type]
            "ciks_indexed": len(_memory_cache.get("by_cik", {})),  # type: ignore[arg-type]
            "names_indexed": len(_memory_cache.get("by_name", {})),  # type: ignore[arg-type]
        },
    }
