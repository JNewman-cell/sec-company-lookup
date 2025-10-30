"""
sec-company-lookup - Fast, cached SEC company data lookups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A lightweight Python package for instant lookups between stock tickers,
CIK identifiers, and company names using the official SEC company_tickers.json dataset.

Basic usage:
    >>> from sec_company_lookup import set_user_email, get_company
    >>> # Configure your email for SEC API compliance
    >>> set_user_email("your@email.com")
    >>> # Data is automatically downloaded when needed
    >>> company = get_company("AAPL")
    >>> print(company)
    [{'cik': 320193, 'ticker': 'AAPL', 'name': 'Apple Inc.'}]

Alternative configuration via environment variable:
    $ export SECCOMPANYLOOKUP_USER_EMAIL="your@email.com"
    >>> from sec_company_lookup import get_company
    >>> company = get_company("AAPL")
"""

from .api.api import (
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
from .config import (
    set_user_email,
    get_user_email,
    clear_user_email,
)
from .types import (
    CompanyData,
    SECCompanyInfo,
    CacheStructure,
)

__version__ = "0.1.0"
__author__ = "Jackson Newman"
__email__ = "jpnewman167@gmail.com"

__all__ = [
    # Main lookup functions
    "get_company",
    "get_companies_by_tickers",
    "get_companies_by_ciks",
    "get_companies_by_names",
    "search_companies",
    "search_companies_by_ticker",
    "search_companies_by_company_name",
    # Data management
    "update_data",
    "clear_cache",
    "get_cache_info",
    # Configuration
    "set_user_email",
    "get_user_email",
    "clear_user_email",
    # Type definitions
    "CompanyData",
    "SECCompanyInfo",
    "CacheStructure",
]


# Auto-initialize data on import
def _auto_initialize() -> None:
    """Automatically ensure data is available on package import."""
    import logging
    from .utils import load_from_cache, is_cache_expired

    logger = logging.getLogger(__name__)

    try:
        # Check if we have cached data and if it's still valid
        cached_data, cached_timestamp = load_from_cache()

        if not cached_data or is_cache_expired(cached_timestamp):
            logger.info(
                "No cached data found or cache expired. "
                "Downloading latest SEC data..."
            )
            # Only update if we don't have data or it's expired
            success = update_data()
            if success:
                logger.info("SEC data successfully downloaded and cached.")
            else:
                logger.warning(
                    "Failed to download SEC data. " "Some functionality may be limited."
                )
        else:
            logger.debug("Using existing cached SEC data.")

    except Exception as e:
        # Don't fail the import if data download fails
        logger.warning(
            f"Failed to auto-initialize SEC data: {e}. "
            "You may need to call update_data() manually."
        )


# Run auto-initialization
_auto_initialize()
