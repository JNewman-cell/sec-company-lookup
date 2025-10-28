"""
Tests for the secmap utilities functionality.
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

from secmap.utils.utils import (
    download_sec_data,
    is_cache_expired,
    load_from_cache,
    normalize_cik,
    clear_cache_files,
    ensure_cache_dir,
)

# Sample test data mimicking SEC structure
SAMPLE_SEC_DATA = {
    "0": {"cik_str": "0000320193", "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": "0000789019", "ticker": "MSFT", "title": "Microsoft Corporation"},
    "2": {"cik_str": "0001652044", "ticker": "GOOGL", "title": "Alphabet Inc."},
    "3": {"cik_str": "0001018724", "ticker": "AMZN", "title": "Amazon.com, Inc."},
    "4": {"cik_str": "0000320193", "ticker": "AAPL-WT", "title": "Apple Inc."},
    "5": {"cik_str": "0001652044", "ticker": "GOOG", "title": "Alphabet Inc."},
}


class TestUtilityFunctions:
    """Test utility functions from utils module."""

    def test_normalize_cik(self):
        """Test CIK normalization functionality."""
        # Test integer input
        assert normalize_cik(320193) == 320193

        # Test string input with leading zeros
        assert normalize_cik("0000320193") == 320193
        assert normalize_cik("000789019") == 789019

        # Test string input without leading zeros
        assert normalize_cik("320193") == 320193
        assert normalize_cik("789019") == 789019

        # Test invalid inputs
        assert normalize_cik("abc123") is None
        assert normalize_cik("123abc") is None
        assert normalize_cik("") is None
        assert normalize_cik("invalid") is None
        assert normalize_cik(None) is None
        assert normalize_cik([]) is None
        assert normalize_cik({}) is None

        # Test edge cases - normalize_cik strips leading zeros, "0" becomes empty string
        assert normalize_cik("0") is None  # "0" becomes empty string after lstrip('0')
        assert normalize_cik("0000000001") == 1  # Leading zeros stripped, becomes "1"
        assert normalize_cik(0) == 0  # Integer input passes through

    def test_is_cache_expired(self):
        """Test cache expiration logic."""
        current_time = time.time()

        # Test non-expired cache (1 hour ago)
        one_hour_ago = current_time - 3600
        assert is_cache_expired(one_hour_ago) is False

        # Test expired cache (25 hours ago, default expiry is 24 hours)
        twenty_five_hours_ago = current_time - (25 * 3600)
        assert is_cache_expired(twenty_five_hours_ago) is True

        # Test no last update (should be expired)
        assert is_cache_expired(0) is True
        assert is_cache_expired(None) is True

        # Test future time (shouldn't happen but should not be expired)
        future_time = current_time + 3600
        assert is_cache_expired(future_time) is False

    def test_ensure_cache_dir(self):
        """Test cache directory creation."""
        with patch("secmap.utils.utils.CACHE_DIR") as mock_cache_dir:
            mock_path = MagicMock()
            mock_cache_dir.__fspath__ = MagicMock(return_value=str(mock_path))
            mock_cache_dir.mkdir = MagicMock()

            ensure_cache_dir()
            mock_cache_dir.mkdir.assert_called_once_with(exist_ok=True)

    @patch("secmap.utils.utils.requests.get")
    @patch("secmap.utils.utils.open", new_callable=mock_open)
    @patch("secmap.utils.utils.ensure_cache_dir")
    def test_download_sec_data_success(self, mock_ensure_dir, mock_file, mock_get):
        """Test successful SEC data download."""
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_SEC_DATA
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = download_sec_data()

        assert result == SAMPLE_SEC_DATA
        mock_get.assert_called_once()
        mock_ensure_dir.assert_called_once()
        mock_file.assert_called_once()

    @patch("secmap.utils.utils.requests.get")
    @patch("secmap.utils.utils.DATA_FILE")
    def test_download_sec_data_failure_with_cache(self, mock_data_file, mock_get):
        """Test SEC data download failure with cache fallback."""
        # Mock the requests module properly
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        # Mock cache file exists and can be read
        mock_data_file.exists.return_value = True
        with patch("builtins.open", mock_open(read_data=json.dumps(SAMPLE_SEC_DATA))):
            result = download_sec_data()
            assert result == SAMPLE_SEC_DATA

    @patch("secmap.utils.utils.requests.get")
    @patch("secmap.utils.utils.DATA_FILE")
    def test_download_sec_data_failure_no_cache(self, mock_data_file, mock_get):
        """Test SEC data download failure without cache."""
        # Mock failed HTTP response
        mock_get.side_effect = Exception("Network error")

        # Mock no cache file
        mock_data_file.exists.return_value = False

        with pytest.raises(Exception):
            download_sec_data()

    @patch("secmap.utils.utils.DATA_FILE")
    def test_load_from_cache_success(self, mock_data_file):
        """Test successful cache loading."""
        # Mock file exists and is not expired
        mock_stat = MagicMock()
        mock_stat.st_mtime = time.time() - 1800  # 30 minutes ago
        mock_data_file.exists.return_value = True
        mock_data_file.stat.return_value = mock_stat

        with patch("builtins.open", mock_open(read_data=json.dumps(SAMPLE_SEC_DATA))):
            data, timestamp = load_from_cache()
            assert data == SAMPLE_SEC_DATA
            assert timestamp == mock_stat.st_mtime

    @patch("secmap.utils.utils.DATA_FILE")
    def test_load_from_cache_expired(self, mock_data_file):
        """Test cache loading with expired file."""
        # Mock file exists but is expired (25 hours old)
        mock_stat = MagicMock()
        mock_stat.st_mtime = time.time() - (25 * 3600)
        mock_data_file.exists.return_value = True
        mock_data_file.stat.return_value = mock_stat

        data, timestamp = load_from_cache()
        assert data is None
        assert timestamp == 0

    @patch("secmap.utils.utils.DATA_FILE")
    def test_load_from_cache_no_file(self, mock_data_file):
        """Test cache loading with no cache file."""
        mock_data_file.exists.return_value = False

        data, timestamp = load_from_cache()
        assert data is None
        assert timestamp == 0

    @patch("secmap.utils.utils.DATA_FILE")
    @patch("secmap.db.db.DB_PATH")
    def test_clear_cache_files(self, mock_db_path, mock_data_file):
        """Test cache file clearing."""
        mock_data_file.exists.return_value = True
        mock_db_path.exists.return_value = True

        clear_cache_files()

        mock_data_file.unlink.assert_called_once()
        mock_db_path.unlink.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
