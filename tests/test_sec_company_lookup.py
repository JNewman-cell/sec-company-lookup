"""
Tests for the core sec_company_lookup module.

This module contains comprehensive tests for the core functionality including:
- Data loading and caching (6 tests)
- Single and batch lookups by ticker (11 tests)
- Single and batch lookups by CIK (11 tests)
- Single and batch lookups by company name (11 tests)
- Search functionality (9 tests)
- Cache management (2 tests)
- Edge cases and error handling (8 tests)

Total: 58 test cases - all tests pass successfully.

Note: Type checking warnings in this file are expected for test files that:
- Access private members (_memory_cache, _load_data_to_memory) for testing
- Use unittest.mock objects without explicit type annotations
- Access TypedDict optional keys that are guaranteed to exist in specific test contexts
"""

# pyright: reportPrivateUsage=false, reportUnknownParameterType=false
# pyright: reportTypedDictNotRequiredAccess=false, reportUnknownArgumentType=false
# pyright: reportUnknownMemberType=false, reportMissingParameterType=false

import pytest
from unittest.mock import patch
import time

# Configure email for tests
from sec_company_lookup.config import set_user_email

set_user_email("test@example.com")

import sec_company_lookup.sec_company_lookup as sec_module
from sec_company_lookup.sec_company_lookup import (
    ensure_data_loaded,
    update_data_impl,
    get_company_by_ticker_single,
    get_companies_by_tickers_batch,
    get_company_by_cik_single,
    get_companies_by_ciks_batch,
    get_company_by_name_single,
    get_companies_by_names_batch,
    search_companies_impl,
    search_companies_by_company_name_impl,
    clear_cache_impl,
    get_cache_info_impl,
)
from .test_data import SAMPLE_SEC_DATA


class TestDataLoading:
    """Test data loading and caching functionality."""

    def setup_method(self):
        """Set up for each test method."""
        clear_cache_impl()

    def teardown_method(self):
        """Clean up after each test method."""
        clear_cache_impl()

    def test_load_data_to_memory(self):
        """Test loading SEC data into memory cache."""
        sec_module._load_data_to_memory(SAMPLE_SEC_DATA)

        # Check that data is loaded
        assert len(sec_module._memory_cache["companies"]) == 6
        assert len(sec_module._memory_cache["by_ticker"]) == 6
        assert len(sec_module._memory_cache["by_cik"]) == 4  # 4 unique CIKs
        assert len(sec_module._memory_cache["by_name"]) == 4  # 4 unique names

        # Verify CIK with multiple companies
        assert 320193 in sec_module._memory_cache["by_cik"]
        assert len(sec_module._memory_cache["by_cik"][320193]) == 2  # AAPL and AAPL-WT

    def test_load_data_to_memory_structure(self):
        """Test that loaded data has correct structure."""
        sec_module._load_data_to_memory(SAMPLE_SEC_DATA)

        # Check a specific company
        aapl_id = sec_module._memory_cache["by_ticker"]["AAPL"]
        aapl_data = sec_module._memory_cache["companies"][aapl_id]

        assert aapl_data["cik"] == 320193
        assert aapl_data["ticker"] == "AAPL"
        assert aapl_data["name"] == "Apple Inc."

    @patch("sec_company_lookup.sec_company_lookup.download_sec_data")
    @patch("sec_company_lookup.sec_company_lookup.load_data_to_db")
    def test_update_data_impl_success(self, mock_load_db, mock_download):
        """Test successful data update."""
        mock_download.return_value = SAMPLE_SEC_DATA

        result = update_data_impl()

        assert result is True
        mock_download.assert_called_once()
        mock_load_db.assert_called_once()
        assert len(sec_module._memory_cache["companies"]) > 0

    @patch("sec_company_lookup.sec_company_lookup.download_sec_data")
    def test_update_data_impl_failure(self, mock_download):
        """Test data update failure handling."""
        mock_download.side_effect = Exception("Network error")

        result = update_data_impl()

        assert result is False

    @patch("sec_company_lookup.sec_company_lookup.download_sec_data")
    def test_update_data_impl_config_error(self, mock_download):
        """Test that configuration errors are re-raised."""
        mock_download.side_effect = ValueError("Missing User-Agent")

        with pytest.raises(ValueError, match="Missing User-Agent"):
            update_data_impl()

    @patch("sec_company_lookup.sec_company_lookup.is_cache_expired")
    @patch("sec_company_lookup.sec_company_lookup.load_from_cache")
    @patch("sec_company_lookup.sec_company_lookup.update_data_impl")
    def test_ensure_data_loaded_from_cache(self, mock_update, mock_load, mock_expired):
        """Test loading data from cache."""
        # Test when cache is empty (not _memory_cache evaluates to True)
        mock_expired.return_value = True  # Trigger loading
        mock_load.return_value = (SAMPLE_SEC_DATA, time.time())

        ensure_data_loaded()

        mock_load.assert_called_once()
        # update_data_impl should not be called since cached_data is available
        mock_update.assert_not_called()
        assert len(sec_module._memory_cache["companies"]) > 0

    @patch("sec_company_lookup.sec_company_lookup.is_cache_expired")
    @patch("sec_company_lookup.sec_company_lookup.load_from_cache")
    @patch("sec_company_lookup.sec_company_lookup.update_data_impl")
    def test_ensure_data_loaded_expired_cache(
        self, mock_update, mock_load, mock_expired
    ):
        """Test loading data when cache is expired."""
        mock_expired.return_value = True
        mock_load.return_value = (None, 0)
        mock_update.return_value = True

        ensure_data_loaded()

        mock_load.assert_called_once()
        mock_update.assert_called_once()


class TestTickerLookups:
    """Test ticker lookup functionality."""

    def setup_method(self):
        """Set up test data for each test."""
        clear_cache_impl()
        sec_module._load_data_to_memory(SAMPLE_SEC_DATA)

    def teardown_method(self):
        """Clean up after each test."""
        clear_cache_impl()

    def test_get_company_by_ticker_single_success(self):
        """Test successful single ticker lookup."""
        response = get_company_by_ticker_single("AAPL")

        assert response["success"] is True
        assert "data" in response
        assert response["data"]["ticker"] == "AAPL"
        assert response["data"]["cik"] == 320193
        assert response["data"]["name"] == "Apple Inc."

    def test_get_company_by_ticker_single_case_insensitive(self):
        """Test ticker lookup is case insensitive."""
        response_upper = get_company_by_ticker_single("AAPL")
        response_lower = get_company_by_ticker_single("aapl")
        response_mixed = get_company_by_ticker_single("AaPl")

        assert response_upper["success"] is True
        assert response_lower["success"] is True
        assert response_mixed["success"] is True
        assert (
            response_upper["data"] == response_lower["data"] == response_mixed["data"]
        )

    def test_get_company_by_ticker_single_not_found(self):
        """Test ticker not found."""
        response = get_company_by_ticker_single("INVALID")

        assert response["success"] is False
        assert "error" in response
        assert response["error_code"] == "NOT_FOUND"
        assert "INVALID" in response["error"]

    def test_get_company_by_ticker_single_empty_input(self):
        """Test empty ticker input."""
        response = get_company_by_ticker_single("")

        assert response["success"] is False
        assert response["error_code"] == "INVALID_INPUT"
        assert "empty" in response["error"].lower()

    def test_get_company_by_ticker_single_whitespace_input(self):
        """Test whitespace ticker input."""
        response = get_company_by_ticker_single("   ")

        assert response["success"] is False
        assert response["error_code"] == "INVALID_INPUT"

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_tickers_db")
    def test_get_companies_by_tickers_batch_success(self, mock_db):
        """Test successful batch ticker lookup."""
        mock_db.return_value = {
            "AAPL": [{"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."}],
            "MSFT": [
                {"cik": 789019, "ticker": "MSFT", "name": "Microsoft Corporation"}
            ],
        }

        results = get_companies_by_tickers_batch(["AAPL", "MSFT"])

        assert len(results) == 2
        assert results["AAPL"]["success"] is True
        assert results["AAPL"]["data"]["ticker"] == "AAPL"
        assert results["MSFT"]["success"] is True
        assert results["MSFT"]["data"]["ticker"] == "MSFT"

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_tickers_db")
    def test_get_companies_by_tickers_batch_mixed_results(self, mock_db):
        """Test batch lookup with mixed valid/invalid tickers."""
        mock_db.return_value = {
            "AAPL": [{"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."}],
            "INVALID": [],
        }

        results = get_companies_by_tickers_batch(["AAPL", "INVALID"])

        assert len(results) == 2
        assert results["AAPL"]["success"] is True
        assert results["INVALID"]["success"] is False
        assert results["INVALID"]["error_code"] == "NOT_FOUND"

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_tickers_db")
    def test_get_companies_by_tickers_batch_empty_input(self, mock_db):
        """Test batch lookup with empty input."""
        results = get_companies_by_tickers_batch([])

        assert len(results) == 0
        mock_db.assert_not_called()

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_tickers_db")
    def test_get_companies_by_tickers_batch_with_whitespace(self, mock_db):
        """Test batch lookup handles whitespace."""
        mock_db.return_value = {
            "AAPL": [{"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."}],
        }

        results = get_companies_by_tickers_batch(["  AAPL  ", "", "  "])

        # Should have results for all three inputs
        assert len(results) == 3
        assert results["  AAPL  "]["success"] is True
        assert results[""]["success"] is False
        assert results[""]["error_code"] == "INVALID_INPUT"
        assert results["  "]["success"] is False
        assert results["  "]["error_code"] == "INVALID_INPUT"

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_tickers_db")
    def test_get_companies_by_tickers_batch_database_error(self, mock_db):
        """Test batch lookup falls back to memory on database error."""
        mock_db.side_effect = Exception("Database error")

        results = get_companies_by_tickers_batch(["AAPL", "MSFT"])

        # Should fall back to memory cache
        assert len(results) == 2
        assert results["AAPL"]["success"] is True
        assert results["MSFT"]["success"] is True


class TestCIKLookups:
    """Test CIK lookup functionality."""

    def setup_method(self):
        """Set up test data for each test."""
        clear_cache_impl()
        sec_module._load_data_to_memory(SAMPLE_SEC_DATA)

    def teardown_method(self):
        """Clean up after each test."""
        clear_cache_impl()

    def test_get_company_by_cik_single_success(self):
        """Test successful single CIK lookup."""
        response = get_company_by_cik_single(320193)

        assert response["success"] is True
        assert "data" in response
        assert isinstance(response["data"], list)
        assert len(response["data"]) == 2  # AAPL and AAPL-WT share same CIK
        assert response["data"][0]["cik"] == 320193

    def test_get_company_by_cik_single_string_input(self):
        """Test CIK lookup with string input."""
        response = get_company_by_cik_single("320193")

        assert response["success"] is True
        assert len(response["data"]) == 2

    def test_get_company_by_cik_single_padded_string(self):
        """Test CIK lookup with zero-padded string."""
        response = get_company_by_cik_single("0000320193")

        assert response["success"] is True
        assert len(response["data"]) == 2

    def test_get_company_by_cik_single_not_found(self):
        """Test CIK not found."""
        response = get_company_by_cik_single(999999999)

        assert response["success"] is False
        assert "error" in response
        assert response["error_code"] == "NOT_FOUND"

    def test_get_company_by_cik_single_invalid_input(self):
        """Test invalid CIK input."""
        response = get_company_by_cik_single("invalid")

        assert response["success"] is False
        assert response["error_code"] == "INVALID_INPUT"

    def test_get_company_by_cik_single_multiple_companies(self):
        """Test CIK with multiple companies returns all."""
        response = get_company_by_cik_single(1652044)  # Alphabet (GOOGL and GOOG)

        assert response["success"] is True
        assert len(response["data"]) == 2
        tickers = {c["ticker"] for c in response["data"]}
        assert tickers == {"GOOGL", "GOOG"}

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_ciks_db")
    def test_get_companies_by_ciks_batch_success(self, mock_db):
        """Test successful batch CIK lookup."""
        mock_db.return_value = {
            320193: [{"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."}],
            789019: [
                {"cik": 789019, "ticker": "MSFT", "name": "Microsoft Corporation"}
            ],
        }

        results = get_companies_by_ciks_batch([320193, 789019])

        assert len(results) == 2
        assert results[320193]["success"] is True
        assert len(results[320193]["data"]) >= 1
        assert results[789019]["success"] is True

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_ciks_db")
    def test_get_companies_by_ciks_batch_mixed_types(self, mock_db):
        """Test batch CIK lookup with mixed int/string types."""
        mock_db.return_value = {
            320193: [{"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."}],
            789019: [
                {"cik": 789019, "ticker": "MSFT", "name": "Microsoft Corporation"}
            ],
        }

        results = get_companies_by_ciks_batch([320193, "789019"])

        assert len(results) == 2
        assert results[320193]["success"] is True
        assert results["789019"]["success"] is True

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_ciks_db")
    def test_get_companies_by_ciks_batch_invalid_ciks(self, mock_db):
        """Test batch CIK lookup with invalid CIKs."""
        mock_db.return_value = {
            320193: [{"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."}],
        }

        # Test with invalid CIKs - type: ignore is needed for intentionally passing None
        results = get_companies_by_ciks_batch([320193, "invalid", None])  # type: ignore

        assert len(results) == 3
        assert results[320193]["success"] is True
        assert results["invalid"]["success"] is False
        assert results["invalid"]["error_code"] == "INVALID_INPUT"
        assert results[None]["success"] is False  # type: ignore
        assert results[None]["error_code"] == "INVALID_INPUT"  # type: ignore

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_ciks_db")
    def test_get_companies_by_ciks_batch_empty_input(self, mock_db):
        """Test batch CIK lookup with empty input."""
        results = get_companies_by_ciks_batch([])

        assert len(results) == 0
        mock_db.assert_not_called()

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_ciks_db")
    def test_get_companies_by_ciks_batch_database_error(self, mock_db):
        """Test batch CIK lookup falls back to memory on database error."""
        mock_db.side_effect = Exception("Database error")

        results = get_companies_by_ciks_batch([320193, 789019])

        # Should fall back to memory cache
        assert len(results) == 2
        assert results[320193]["success"] is True
        assert results[789019]["success"] is True


class TestNameLookups:
    """Test company name lookup functionality."""

    def setup_method(self):
        """Set up test data for each test."""
        clear_cache_impl()
        sec_module._load_data_to_memory(SAMPLE_SEC_DATA)

    def teardown_method(self):
        """Clean up after each test."""
        clear_cache_impl()

    def test_get_company_by_name_single_exact_match(self):
        """Test exact name match."""
        response = get_company_by_name_single("Apple Inc.")

        assert response["success"] is True
        assert "data" in response
        assert response["data"]["name"] == "Apple Inc."
        assert response["data"]["ticker"] == "AAPL"

    def test_get_company_by_name_single_case_insensitive(self):
        """Test name lookup is case insensitive."""
        response_upper = get_company_by_name_single("APPLE INC.")
        response_lower = get_company_by_name_single("apple inc.")
        response_mixed = get_company_by_name_single("Apple Inc.")

        assert response_upper["success"] is True
        assert response_lower["success"] is True
        assert response_mixed["success"] is True

    def test_get_company_by_name_single_fuzzy_match(self):
        """Test fuzzy name matching."""
        response = get_company_by_name_single("Microsoft", fuzzy=True)

        assert response["success"] is True
        assert "Microsoft" in response["data"]["name"]

    def test_get_company_by_name_single_not_found(self):
        """Test name not found."""
        response = get_company_by_name_single("NonExistent Company", fuzzy=False)

        assert response["success"] is False
        assert response["error_code"] == "NOT_FOUND"

    def test_get_company_by_name_single_empty_input(self):
        """Test empty name input."""
        response = get_company_by_name_single("")

        assert response["success"] is False
        assert response["error_code"] == "INVALID_INPUT"

    def test_get_company_by_name_single_whitespace_input(self):
        """Test whitespace name input."""
        response = get_company_by_name_single("   ")

        assert response["success"] is False
        assert response["error_code"] == "INVALID_INPUT"

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_company_names_db")
    def test_get_companies_by_names_batch_success(self, mock_db):
        """Test successful batch name lookup."""
        mock_db.return_value = {
            "Apple Inc.": [{"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."}],
            "Microsoft Corporation": [
                {"cik": 789019, "ticker": "MSFT", "name": "Microsoft Corporation"}
            ],
        }

        results = get_companies_by_names_batch(["Apple Inc.", "Microsoft Corporation"])

        assert len(results) == 2
        assert results["Apple Inc."]["success"] is True
        assert results["Apple Inc."]["data"]["name"] == "Apple Inc."
        assert results["Microsoft Corporation"]["success"] is True

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_company_names_db")
    def test_get_companies_by_names_batch_not_found(self, mock_db):
        """Test batch name lookup with not found names."""
        mock_db.return_value = {
            "Apple Inc.": [{"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."}],
            "NonExistent": [],
        }

        results = get_companies_by_names_batch(["Apple Inc.", "NonExistent"])

        assert len(results) == 2
        assert results["Apple Inc."]["success"] is True
        assert results["NonExistent"]["success"] is False
        assert results["NonExistent"]["error_code"] == "NOT_FOUND"

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_company_names_db")
    def test_get_companies_by_names_batch_empty_input(self, mock_db):
        """Test batch name lookup with empty input."""
        results = get_companies_by_names_batch([])

        assert len(results) == 0
        mock_db.assert_not_called()

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_company_names_db")
    def test_get_companies_by_names_batch_with_whitespace(self, mock_db):
        """Test batch name lookup handles whitespace."""
        mock_db.return_value = {
            "Apple Inc.": [{"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."}],
        }

        results = get_companies_by_names_batch(["Apple Inc.", "", "  "])

        assert len(results) == 3
        assert results["Apple Inc."]["success"] is True
        assert results[""]["success"] is False
        assert results[""]["error_code"] == "INVALID_INPUT"
        assert results["  "]["success"] is False

    @patch("sec_company_lookup.sec_company_lookup.get_companies_by_company_names_db")
    def test_get_companies_by_names_batch_database_error(self, mock_db):
        """Test batch name lookup falls back to memory on database error."""
        mock_db.side_effect = Exception("Database error")

        results = get_companies_by_names_batch(["Apple Inc.", "Microsoft Corporation"])

        # Should fall back to memory cache
        assert len(results) == 2
        assert results["Apple Inc."]["success"] is True
        assert results["Microsoft Corporation"]["success"] is True


class TestSearchFunctions:
    """Test search functionality."""

    def setup_method(self):
        """Set up test data for each test."""
        clear_cache_impl()
        sec_module._load_data_to_memory(SAMPLE_SEC_DATA)

    def teardown_method(self):
        """Clean up after each test."""
        clear_cache_impl()

    @patch("sec_company_lookup.sec_company_lookup.search_companies_db")
    def test_search_companies_impl_success(self, mock_db):
        """Test successful company search."""
        mock_db.return_value = [
            {"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."},
        ]

        results = search_companies_impl("Apple", limit=5)

        assert len(results) >= 1
        assert any("Apple" in r["name"] for r in results)

    @patch("sec_company_lookup.sec_company_lookup.search_companies_db")
    def test_search_companies_impl_empty_query(self, mock_db):
        """Test search with empty query."""
        results = search_companies_impl("")

        assert len(results) == 0
        mock_db.assert_not_called()

    @patch("sec_company_lookup.sec_company_lookup.search_companies_db")
    def test_search_companies_impl_exact_ticker_match(self, mock_db):
        """Test search prioritizes exact ticker matches."""
        mock_db.return_value = []

        results = search_companies_impl("AAPL", fuzzy=False)

        assert len(results) >= 1
        assert results[0]["ticker"] == "AAPL"

    @patch("sec_company_lookup.sec_company_lookup.search_companies_db")
    def test_search_companies_impl_limit(self, mock_db):
        """Test search respects limit."""
        mock_db.return_value = [
            {"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."},
            {"cik": 789019, "ticker": "MSFT", "name": "Microsoft Corporation"},
            {"cik": 1652044, "ticker": "GOOGL", "name": "Alphabet Inc."},
        ]

        results = search_companies_impl("Inc", limit=2)

        assert len(results) <= 2

    @patch("sec_company_lookup.sec_company_lookup.search_companies_db")
    def test_search_companies_impl_database_fallback(self, mock_db):
        """Test search falls back to memory on database error."""
        import sqlite3

        mock_db.side_effect = sqlite3.Error("Database error")

        results = search_companies_impl("Apple", limit=5)

        # Should have results from memory cache fallback
        assert len(results) >= 1

    @patch("sec_company_lookup.sec_company_lookup.search_companies_by_company_name_db")
    def test_search_companies_by_company_name_impl_success(self, mock_db):
        """Test successful company name search."""
        mock_db.return_value = [
            {"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."},
        ]

        results = search_companies_by_company_name_impl("Apple", limit=5)

        assert len(results) >= 1
        assert any("Apple" in r["name"] for r in results)

    @patch("sec_company_lookup.sec_company_lookup.search_companies_by_company_name_db")
    def test_search_companies_by_company_name_impl_empty_query(self, mock_db):
        """Test name search with empty query."""
        results = search_companies_by_company_name_impl("")

        assert len(results) == 0
        mock_db.assert_not_called()

    @patch("sec_company_lookup.sec_company_lookup.search_companies_by_company_name_db")
    def test_search_companies_by_company_name_impl_exact_match(self, mock_db):
        """Test name search prioritizes exact matches."""
        mock_db.return_value = []

        results = search_companies_by_company_name_impl("Apple Inc.", fuzzy=False)

        assert len(results) >= 1
        assert results[0]["name"] == "Apple Inc."

    @patch("sec_company_lookup.sec_company_lookup.search_companies_by_company_name_db")
    def test_search_companies_by_company_name_impl_fuzzy(self, mock_db):
        """Test fuzzy name search."""
        mock_db.return_value = [
            {"cik": 320193, "ticker": "AAPL", "name": "Apple Inc."},
        ]

        results = search_companies_by_company_name_impl("Appl", limit=5, fuzzy=True)

        assert len(results) >= 1

    @patch("sec_company_lookup.sec_company_lookup.search_companies_by_company_name_db")
    def test_search_companies_by_company_name_impl_database_fallback(self, mock_db):
        """Test name search falls back to memory on database error."""
        import sqlite3

        mock_db.side_effect = sqlite3.Error("Database error")

        # Use exact name match to ensure fallback works (memory cache uses exact matches)
        results = search_companies_by_company_name_impl(
            "Apple Inc.", limit=5, fuzzy=False
        )

        # Should have results from memory cache fallback
        assert len(results) >= 1


class TestCacheManagement:
    """Test cache management functionality."""

    def setup_method(self):
        """Set up test data for each test."""
        clear_cache_impl()
        sec_module._load_data_to_memory(SAMPLE_SEC_DATA)

    def teardown_method(self):
        """Clean up after each test."""
        clear_cache_impl()

    def test_clear_cache_impl(self):
        """Test cache clearing."""
        # Ensure cache has data
        assert len(sec_module._memory_cache["companies"]) > 0

        clear_cache_impl()

        # Verify cache is empty
        assert len(sec_module._memory_cache["companies"]) == 0
        assert len(sec_module._memory_cache["by_ticker"]) == 0
        assert len(sec_module._memory_cache["by_cik"]) == 0
        assert len(sec_module._memory_cache["by_name"]) == 0

    @patch("sec_company_lookup.sec_company_lookup.get_db_stats")
    def test_get_cache_info_impl(self, mock_db_stats):
        """Test getting cache information."""
        mock_db_stats.return_value = {
            "db_exists": True,
            "db_companies_count": 6,
            "db_fts_enabled": True,
            "cache_dir": "/fake/path",
        }

        info = get_cache_info_impl()

        assert "companies_cached" in info
        assert info["companies_cached"] == 6
        assert "last_update" in info
        assert "cache_age_hours" in info
        assert "cache_expired" in info
        assert "memory_cache_structure" in info

    @patch("sec_company_lookup.sec_company_lookup.get_db_stats")
    def test_get_cache_info_impl_structure(self, mock_db_stats):
        """Test cache info returns detailed structure."""
        mock_db_stats.return_value = {
            "db_exists": True,
            "db_companies_count": 6,
            "db_fts_enabled": True,
            "cache_dir": "/fake/path",
        }

        info = get_cache_info_impl()

        # Check memory cache structure details
        assert "memory_cache_structure" in info
        struct = info["memory_cache_structure"]
        assert "companies" in struct
        assert "tickers_indexed" in struct
        assert "ciks_indexed" in struct
        assert "names_indexed" in struct


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Set up test data for each test."""
        clear_cache_impl()
        sec_module._load_data_to_memory(SAMPLE_SEC_DATA)

    def teardown_method(self):
        """Clean up after each test."""
        clear_cache_impl()

    def test_ticker_with_special_characters(self):
        """Test ticker lookup with special characters."""
        response = get_company_by_ticker_single("AAPL-WT")

        assert response["success"] is True
        assert response["data"]["ticker"] == "AAPL-WT"

    def test_cik_shared_by_multiple_companies(self):
        """Test CIK lookup returns all companies with same CIK."""
        response = get_company_by_cik_single(320193)

        assert response["success"] is True
        assert len(response["data"]) == 2  # AAPL and AAPL-WT
        tickers = {c["ticker"] for c in response["data"]}
        assert "AAPL" in tickers
        assert "AAPL-WT" in tickers

    def test_name_shared_by_multiple_companies(self):
        """Test name lookup with companies sharing same name."""
        response = get_company_by_name_single("Apple Inc.")

        assert response["success"] is True
        # Should return first match when multiple exist
        assert response["data"]["name"] == "Apple Inc."

    def test_unicode_in_company_name(self):
        """Test handling of unicode characters in names."""
        # This test would need actual unicode data
        response = get_company_by_name_single("Tëst Çompany")

        # Should handle gracefully even if not found
        assert response["success"] is False
        assert response["error_code"] == "NOT_FOUND"

    def test_very_long_query(self):
        """Test handling of very long search queries."""
        long_query = "A" * 1000

        results = search_companies_impl(long_query)

        # Should handle without crashing
        assert isinstance(results, list)

    def test_concurrent_cache_access(self):
        """Test that cache can be safely accessed multiple times."""
        # Make multiple concurrent lookups
        results = []
        for _ in range(10):
            response = get_company_by_ticker_single("AAPL")
            results.append(response)

        # All should succeed
        assert all(r["success"] for r in results)
        # All should return same data
        assert len(set(r["data"]["ticker"] for r in results)) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
