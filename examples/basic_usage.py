
"""
Example usage for sec_company_lookup package.
Demonstrates basic lookups, search, batch operations, and cache info.
"""

from typing import Dict, Any, cast
from sec_company_lookup import (
    set_user_email,
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
from sec_company_lookup.types import CompanyData


# ============================================================================
# CONFIGURATION
# ============================================================================

# Configure email for SEC API compliance (required)
set_user_email("your@email.com")

# Alternative: Set environment variable SECCOMPANYLOOKUP_USER_EMAIL


# ============================================================================
# SINGLE LOOKUPS
# ============================================================================

# Lookup by ticker (returns CompanyData or None)
company = get_companies_by_tickers("AAPL")
# Returns: {'cik': 320193, 'ticker': 'AAPL', 'name': 'Apple Inc.'}

# Lookup by CIK (returns List[CompanyData])
companies = get_companies_by_ciks(320193)
# Returns: [{'cik': 320193, 'ticker': 'AAPL', 'name': 'Apple Inc.'}]

# Lookup by company name (returns CompanyData or None)
company = get_companies_by_names("Apple Inc.")
# Returns: {'cik': 320193, 'ticker': 'AAPL', 'name': 'Apple Inc.'}

# Smart lookup - auto-detects input type (returns List[CompanyData])
companies = get_company("MSFT")  # Ticker
companies = get_company("789019")  # CIK
companies = get_company("Microsoft Corporation")  # Name


# ============================================================================
# BATCH LOOKUPS
# ============================================================================

# Batch ticker lookup (returns Dict[str, BatchLookupResponse])
batch_results = get_companies_by_tickers(["AAPL", "MSFT", "GOOGL", "INVALID"])
# Returns: {
#   "AAPL": {"success": True, "data": {...}},
#   "MSFT": {"success": True, "data": {...}},
#   "GOOGL": {"success": True, "data": {...}},
#   "INVALID": {"success": False, "error": "Ticker 'INVALID' not found", "error_code": "NOT_FOUND"}
# }

# Process batch results (works same for tickers and names - both return BatchLookupResponse)
if isinstance(batch_results, dict):
    for ticker, response in batch_results.items():
        response_dict = cast(Dict[str, Any], response)
        if response_dict["success"]:
            data = cast(CompanyData, response_dict.get("data"))
            # Process successful lookup: data['name'], data['cik'], data['ticker']
            pass
        else:
            # Handle error: response_dict['error'], response_dict['error_code']
            pass

# Batch CIK lookup (returns Dict[int|str, MultipleLookupResponse])
# Note: CIKs can map to multiple companies (e.g., different share classes)
batch_results_cik = get_companies_by_ciks([320193, 789019, 1652044])
# Returns: {
#   320193: {"success": True, "data": [{'cik': 320193, 'ticker': 'AAPL', 'name': 'Apple Inc.'}]},
#   789019: {"success": True, "data": [{'cik': 789019, 'ticker': 'MSFT', 'name': 'MICROSOFT CORP'}]},
#   1652044: {"success": True, "data": [{'cik': 1652044, 'ticker': 'GOOGL', 'name': 'Alphabet Inc.'}]}
# }

# Batch name lookup (returns Dict[str, BatchLookupResponse])
# Note: Returns single best match per name (same structure as ticker batch lookup)
batch_results_names = get_companies_by_names(["Apple Inc.", "Microsoft Corporation"])
# Returns: {
#   "Apple Inc.": {"success": True, "data": {'cik': 320193, 'ticker': 'AAPL', 'name': 'Apple Inc.'}},
#   "Microsoft Corporation": {"success": True, "data": {'cik': 789019, 'ticker': 'MSFT', ...}}
# }

# Process batch name results (same structure as batch ticker results)
if isinstance(batch_results_names, dict):
    for name, response in batch_results_names.items():
        response_dict = cast(Dict[str, Any], response)
        if response_dict["success"]:
            data = cast(CompanyData, response_dict.get("data"))
            # Process successful lookup: data['name'], data['cik'], data['ticker']
            pass
        else:
            # Handle error: response_dict['error'], response_dict['error_code']
            pass


# ============================================================================
# SEARCH FUNCTIONS
# ============================================================================

# General search (searches all fields)
results = search_companies("Apple", limit=5)
# Returns: [{'cik': ..., 'ticker': ..., 'name': ...}, ...]

# Search by ticker
results = search_companies_by_ticker("GOOG", limit=3)

# Search by company name (more precise)
results = search_companies_by_company_name("Microsoft", limit=3)

# Fuzzy search (partial matches)
results = search_companies_by_company_name("Micros", limit=5, fuzzy=True)

# Exact search (no fuzzy matching)
results = search_companies_by_company_name("Apple Inc.", fuzzy=False)


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

# Get cache information
cache_info = get_cache_info()
# Returns: {
#   'memory_cache_loaded': True,
#   'memory_companies_count': 13000,
#   'last_update_human': '2024-10-30 12:00:00',
#   'cache_age_hours': 0.5,
#   'cache_expired': False,
#   'db_exists': True,
#   'db_companies_count': 13000,
#   'cache_dir': '/path/to/.sec_company_lookup'
# }

# Manually update data from SEC API (optional, auto-updates on import)
success = update_data()

# Clear all cache (forces re-download on next lookup)
clear_cache()


# ============================================================================
# ERROR HANDLING
# ============================================================================

# Single ticker/name lookup returns None if not found
company = get_companies_by_tickers("INVALID")  # Returns: None
company = get_companies_by_names("Invalid Company Name")  # Returns: None

# Single CIK lookup returns empty list if not found (CIKs can have multiple matches)
companies = get_companies_by_ciks(99999999)  # Returns: []

# Batch lookups return structured error responses
results = get_companies_by_tickers(["AAPL", "INVALID"])
# Returns: {
#   "AAPL": {"success": True, "data": {...}},
#   "INVALID": {"success": False, "error": "...", "error_code": "NOT_FOUND"}
# }

# Empty input handling
search_companies("")  # Returns: []
get_companies_by_tickers([])  # Returns: {}
