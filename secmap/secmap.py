"""
Core secmap module for SEC company data lookups.

This module provides fast, cached lookups between stock tickers, CIK identifiers,
and company names using the official SEC company_tickers.json dataset.
"""

import sqlite3
from functools import lru_cache
from typing import Dict, List, Optional, Union, Any
import time
import logging

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
    search_companies_by_company_name_db,
    get_companies_by_sector_search_db,
    get_db_stats,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global in-memory cache
_memory_cache: Dict[str, Any] = {}
_last_update: float = 0


def _load_data_to_memory(data: Dict[str, Any]) -> None:
    """Load company data into memory cache with optimized structure supporting multiple matches."""
    global _memory_cache, _last_update

    # Use a more memory-efficient structure
    # Store each company once and reference by ID
    companies = {}  # id -> company_data
    ticker_index: Dict[str, str] = {}  # ticker -> id (one-to-one for tickers)
    cik_index: Dict[int, List[str]] = {}  # cik -> list of ids (one-to-many for CIKs)
    name_index: Dict[str, List[str]] = {}  # name -> list of ids (one-to-many for names)

    company_id_counter = 0
    for key, company_info in data.items():
        if isinstance(company_info, dict):
            cik_raw = company_info.get("cik_str", "")
            ticker = company_info.get("ticker", "").upper()
            title = company_info.get("title", "")

            cik_int = normalize_cik(cik_raw)

            if cik_int is not None and ticker and title:
                company_id = str(company_id_counter)
                company_data = {"cik": cik_int, "ticker": ticker, "title": title}

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
        f"Found {multi_cik_count} CIKs with multiple companies, {multi_name_count} names with multiple companies"
    )


def _ensure_data_loaded() -> None:
    """Ensure data is loaded, updating if necessary."""
    global _last_update

    if not _memory_cache or is_cache_expired(_last_update):
        cached_data, cached_timestamp = load_from_cache()
        if cached_data:
            _load_data_to_memory(cached_data)
            _last_update = cached_timestamp
        else:
            if not update_data():
                raise RuntimeError(
                    "Unable to load SEC company data. Please check your internet connection."
                )


def update_data() -> bool:
    """
    Download and cache the latest SEC company data.

    Returns:
        bool: True if data was successfully updated, False otherwise.
    """
    try:
        data = download_sec_data()
        _load_data_to_memory(data)
        load_data_to_db(data)  # Database for search operations

        # Clear function-level caches after update to ensure fresh data
        get_company_by_ticker.cache_clear()
        get_company_by_cik.cache_clear()

        return True
    except Exception as e:
        logger.error(f"Failed to update data: {e}")
        return False


@lru_cache(maxsize=1000)
def get_company_by_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Look up company information by ticker symbol.

    Args:
        ticker (str): Stock ticker symbol (e.g., "AAPL")

    Returns:
        Dict containing cik, ticker, and name, or None if not found.
    """
    if not ticker or not ticker.strip():
        return None

    _ensure_data_loaded()
    company_id = _memory_cache["by_ticker"].get(ticker.strip().upper())  # type: ignore[attr-defined]
    if company_id is not None:
        return _memory_cache["companies"][company_id]  # type: ignore[no-any-return,index]
    return None


@lru_cache(maxsize=1000)
def get_company_by_cik(cik: Union[int, str]) -> List[Dict[str, Any]]:
    """
    Look up company information by CIK identifier.

    Args:
        cik (Union[int, str]): CIK identifier

    Returns:
        List of dicts containing cik, ticker, and name, or empty list if not found.
        Multiple companies can have the same CIK (e.g., different ticker classes).
    """
    _ensure_data_loaded()

    # Convert to int if string
    cik_int = normalize_cik(cik)
    if cik_int is None:
        return []

    company_ids = _memory_cache["by_cik"].get(cik_int, [])  # type: ignore[attr-defined]
    return [_memory_cache["companies"][company_id] for company_id in company_ids]  # type: ignore[index]


def get_company_by_name(name: str, fuzzy: bool = False) -> List[Dict[str, Any]]:
    """
    Look up company information by company name.

    Args:
        name (str): Company name
        fuzzy (bool): If True, perform fuzzy matching

    Returns:
        List of dicts containing cik, ticker, and name, or empty list if not found.
        Multiple companies can have the same or similar names.
    """
    if not name or not name.strip():
        return []

    _ensure_data_loaded()
    results = []
    seen_company_ids = set()

    # Exact match first
    name_lower = name.strip().lower()
    company_ids = _memory_cache["by_name"].get(name_lower, [])  # type: ignore[attr-defined]
    for company_id in company_ids:
        if company_id not in seen_company_ids:
            results.append(_memory_cache["companies"][company_id])  # type: ignore[index]
            seen_company_ids.add(company_id)

    # Fuzzy matching if requested and no exact matches found
    if fuzzy and not results:
        for cached_name, comp_ids in _memory_cache["by_name"].items():  # type: ignore[attr-defined]
            if name_lower in cached_name or cached_name in name_lower:
                for comp_id in comp_ids:
                    if comp_id not in seen_company_ids:
                        results.append(_memory_cache["companies"][comp_id])  # type: ignore[index]
                        seen_company_ids.add(comp_id)

    return results


def get_company(identifier: Union[str, int]) -> List[Dict[str, Any]]:
    """
    Smart lookup that tries to determine the type of identifier.

    Args:
        identifier (Union[str, int]): Ticker, CIK, or company name

    Returns:
        List of dicts containing cik, ticker, and name, or empty list if not found.
        For ticker lookups, list will contain at most one item.
        For CIK/name lookups, list may contain multiple items.
    """
    if identifier is None:
        return []

    _ensure_data_loaded()

    if isinstance(identifier, int):
        return get_company_by_cik(identifier)

    if isinstance(identifier, str):
        # Check for empty or whitespace-only strings
        if not identifier.strip():
            return []

        # Try ticker first (most common case)
        ticker_result = get_company_by_ticker(identifier)
        if ticker_result:
            return [ticker_result]  # Wrap single result in list for consistency

        # Try CIK if it's numeric
        if identifier.strip().isdigit():
            cik_result = get_company_by_cik(identifier)
            if cik_result:
                return cik_result

        # Try company name
        return get_company_by_name(identifier, fuzzy=True)

    return []


def search_companies(
    query: str, limit: int = 10, fuzzy: bool = True
) -> List[Dict[str, Any]]:
    """
    Search for companies by partial name or ticker match.

    Args:
        query (str): Search query
        limit (int): Maximum number of results to return
        fuzzy (bool): If True, perform fuzzy matching; if False, exact matching only

    Returns:
        List of matching company dictionaries.
    """
    _ensure_data_loaded()

    if not query or not query.strip():
        return []

    # First check in-memory cache for exact matches
    results = []
    seen_ids = set()
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
) -> List[Dict[str, Any]]:
    """Fallback in-memory search for companies."""
    results = []
    seen_ids = set()
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


def get_companies_by_ciks(
    ciks: List[Union[int, str]],
) -> Dict[Union[int, str], List[Dict[str, Any]]]:
    """
    Batch lookup companies by multiple CIK identifiers using database for efficiency.

    Args:
        ciks: List of CIK identifiers

    Returns:
        Dict mapping each CIK to list of matching companies
    """
    if not ciks:
        return {}

    _ensure_data_loaded()

    # Normalize CIKs to integers
    normalized_ciks = []
    cik_mapping: Dict[int, List[Any]] = {}  # maps normalized CIK back to original

    for original_cik in ciks:
        normalized_cik = normalize_cik(original_cik)
        if normalized_cik is not None:
            normalized_ciks.append(normalized_cik)
            if normalized_cik not in cik_mapping:
                cik_mapping[normalized_cik] = []
            cik_mapping[normalized_cik].append(original_cik)

    if not normalized_ciks:
        return {cik: [] for cik in ciks}

    try:
        db_results = get_companies_by_ciks_db(normalized_ciks)

        # Map back to original CIK formats
        results = {}
        for normalized_cik, companies in db_results.items():
            for original_cik in cik_mapping[normalized_cik]:
                results[original_cik] = companies

        # Ensure all requested CIKs are in the result (even if empty)
        for original_cik in ciks:
            if original_cik not in results:
                results[original_cik] = []

        return results

    except sqlite3.Error as e:
        logger.warning(
            f"Database batch lookup failed, falling back to individual lookups: {e}"
        )
        # Fallback to individual lookups
        return {cik: get_company_by_cik(cik) for cik in ciks}


def get_companies_by_company_names(
    company_names: List[str], fuzzy: bool = True
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Batch lookup companies by multiple company names.

    Args:
        company_names: List of company names
        fuzzy: If True, perform fuzzy matching; if False, exact matching only

    Returns:
        Dict mapping each company name to list of matching companies
    """
    if not company_names:
        return {}

    _ensure_data_loaded()

    # First check in-memory cache for exact matches
    results: Dict[str, List[Dict[str, Any]]] = {}
    remaining_names = []

    for company_name in company_names:
        if not company_name or not company_name.strip():
            results[company_name] = []
            continue

        query_lower = company_name.strip().lower()
        company_ids = _memory_cache["by_name"].get(query_lower, [])  # type: ignore[attr-defined]

        if company_ids:
            # Found exact match in cache
            results[company_name] = [
                _memory_cache["companies"][company_id] for company_id in company_ids  # type: ignore[index]
            ]
            if not fuzzy:
                # If not fuzzy, we're done with this name
                continue
        else:
            # No exact match found
            results[company_name] = []

        # If fuzzy is enabled or no exact match found, we need to check database
        if fuzzy or not results[company_name]:
            remaining_names.append(company_name)

    # Query database for remaining names
    if remaining_names:
        try:
            db_results = get_companies_by_company_names_db(remaining_names, fuzzy)

            # Merge database results, avoiding duplicates
            for name, db_companies in db_results.items():
                existing_companies = results.get(name, [])
                existing_pairs = {(c["cik"], c["ticker"]) for c in existing_companies}

                for db_company in db_companies:
                    if (db_company["cik"], db_company["ticker"]) not in existing_pairs:
                        results[name].append(db_company)
                        existing_pairs.add((db_company["cik"], db_company["ticker"]))

        except sqlite3.Error as e:
            logger.warning(
                f"Database batch company name lookup failed, falling back to memory search: {e}"
            )
            # Fallback to memory-based search for remaining names
            for company_name in remaining_names:
                if company_name not in results:
                    results[company_name] = []

                fallback_results = get_company_by_name(company_name, fuzzy=fuzzy)
                existing_pairs = {
                    (c["cik"], c["ticker"]) for c in results[company_name]
                }

                for fallback_result in fallback_results:
                    if (
                        fallback_result["cik"],
                        fallback_result["ticker"],
                    ) not in existing_pairs:
                        results[company_name].append(fallback_result)

    return results


def search_companies_by_company_name(
    company_name_query: str, limit: int = 10, fuzzy: bool = True
) -> List[Dict[str, Any]]:
    """
    Search for companies by company name with various matching options.

    Args:
        company_name_query: Company name search query
        limit: Maximum number of results to return
        fuzzy: If True, perform fuzzy matching; if False, exact matching only

    Returns:
        List of matching company dictionaries
    """
    if not company_name_query or not company_name_query.strip():
        return []

    _ensure_data_loaded()

    # First check in-memory cache for exact matches
    results = []
    seen_ids = set()
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
                    results.append(db_result)

        except sqlite3.Error as e:
            logger.warning(
                f"Database company name search failed, falling back to memory search: {e}"
            )
            # Fallback to existing memory-based name search
            fallback_results = get_company_by_name(query_stripped, fuzzy=fuzzy)[:limit]

            # Add fallback results, avoiding duplicates
            for fallback_result in fallback_results:
                if len(results) >= limit:
                    break
                is_duplicate = any(
                    r["cik"] == fallback_result["cik"]
                    and r["ticker"] == fallback_result["ticker"]
                    for r in results
                )
                if not is_duplicate:
                    results.append(fallback_result)

    return results[:limit]


def get_companies_by_sector_search(
    sector_keywords: List[str], limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Search for companies by sector-related keywords in company names.

    Args:
        sector_keywords: List of keywords to search for (e.g., ['bank', 'financial'])
        limit: Maximum number of results

    Returns:
        List of matching companies
    """
    if not sector_keywords:
        return []

    _ensure_data_loaded()

    try:
        return get_companies_by_sector_search_db(sector_keywords, limit)
    except Exception as e:
        logger.error(f"Sector search failed: {e}")
        return []


def clear_cache() -> None:
    """Clear all cached data including database."""
    global _memory_cache, _last_update

    _memory_cache = {}
    _last_update = 0

    # Clear LRU caches
    get_company_by_ticker.cache_clear()
    get_company_by_cik.cache_clear()

    # Remove cache files
    clear_cache_files()

    logger.info("Cache cleared")


def get_cache_info() -> Dict[str, Any]:
    """
    Get information about the current cache status.

    Returns:
        Dict with cache statistics and status.
    """
    _ensure_data_loaded()

    # Get database stats
    db_stats = get_db_stats()

    return {
        "companies_cached": len(_memory_cache.get("companies", {})),  # type: ignore[arg-type]
        "last_update": _last_update,
        "cache_age_hours": (
            (time.time() - _last_update) / 3600 if _last_update else None
        ),
        "cache_expired": is_cache_expired(_last_update),
        "ticker_cache_info": get_company_by_ticker.cache_info()._asdict(),
        "cik_cache_info": get_company_by_cik.cache_info()._asdict(),
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
