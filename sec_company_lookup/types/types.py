"""
Type definitions for the sec-company-lookup package.

This module contains all TypedDict definitions and type aliases used throughout
the package for better type safety and code organization.
"""

from typing import Dict, List, TypedDict
from typing_extensions import NotRequired


class CompanyData(TypedDict):
    """Type definition for company data dictionary returned by lookup functions."""

    cik: int
    ticker: str
    name: str


class SECCompanyInfo(TypedDict):
    """Type definition for SEC API company info from company_tickers.json."""

    cik_str: str
    ticker: str
    title: str


class CacheStructure(TypedDict):
    """Type definition for the memory cache structure."""

    companies: Dict[str, CompanyData]
    by_ticker: Dict[str, str]
    by_cik: Dict[int, List[str]]
    by_name: Dict[str, List[str]]


class SingleLookupResponse(TypedDict):
    """Response structure for single lookup operations.
    
    On success: includes 'data', excludes 'error' and 'error_code'
    On failure: includes 'error' and 'error_code', excludes 'data'
    """

    success: bool
    data: NotRequired[CompanyData]
    error: NotRequired[str]
    error_code: NotRequired[str]


class BatchLookupResponse(TypedDict):
    """Response structure for individual items in batch operations.
    
    On success: includes 'data', excludes 'error' and 'error_code'
    On failure: includes 'error' and 'error_code', excludes 'data'
    """

    success: bool
    data: NotRequired[CompanyData]
    error: NotRequired[str]
    error_code: NotRequired[str]


class MultipleLookupResponse(TypedDict):
    """Response structure for lookups that can return multiple companies (CIK, name).
    
    On success: includes 'data', excludes 'error' and 'error_code'
    On failure: includes 'error' and 'error_code', excludes 'data'
    """

    success: bool
    data: NotRequired[List[CompanyData]]
    error: NotRequired[str]
    error_code: NotRequired[str]
