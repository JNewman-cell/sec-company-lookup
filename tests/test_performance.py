"""
Performance benchmarks for secmap package.

Run with: pytest tests/test_performance.py -v --benchmark-only
"""

import pytest
import time
from unittest.mock import patch

from secmap.secmap import (
    get_company,
    get_company_by_ticker,
    get_company_by_cik,
    search_companies,
    get_companies_by_ciks,
    _memory_cache
)

# Sample test data
SAMPLE_SEC_DATA_CACHE = {
    'companies': {
        '0': {'cik': 320193, 'ticker': 'AAPL', 'name': 'Apple Inc.'},
        '1': {'cik': 789019, 'ticker': 'MSFT', 'name': 'Microsoft Corporation'},
        '2': {'cik': 1652044, 'ticker': 'GOOGL', 'name': 'Alphabet Inc.'},
        '3': {'cik': 1018724, 'ticker': 'AMZN', 'name': 'Amazon.com, Inc.'},
    },
    'ticker_index': {'AAPL': '0', 'MSFT': '1', 'GOOGL': '2', 'AMZN': '3'},
    'cik_index': {320193: ['0'], 789019: ['1'], 1652044: ['2'], 1018724: ['3']},
    'name_index': {
        'Apple Inc.': ['0'], 'Microsoft Corporation': ['1'], 
        'Alphabet Inc.': ['2'], 'Amazon.com, Inc.': ['3']
    }
}


class TestPerformance:
    """Performance benchmarks for secmap operations."""
    
    def setup_method(self):
        """Setup test environment with sample data."""
        global _memory_cache
        _memory_cache.clear()
        _memory_cache.update(SAMPLE_SEC_DATA_CACHE)
    
    def teardown_method(self):
        """Clean up after tests."""
        global _memory_cache
        _memory_cache.clear()

    @pytest.mark.benchmark
    def test_ticker_lookup_performance(self, benchmark):
        """Benchmark ticker lookup performance."""
        result = benchmark(get_company_by_ticker, "AAPL")
        assert len(result) == 1
        assert result[0]['ticker'] == 'AAPL'

    @pytest.mark.benchmark  
    def test_cik_lookup_performance(self, benchmark):
        """Benchmark CIK lookup performance."""
        result = benchmark(get_company_by_cik, 320193)
        assert len(result) == 1
        assert result[0]['cik'] == 320193

    @pytest.mark.benchmark
    def test_smart_lookup_performance(self, benchmark):
        """Benchmark smart lookup auto-detection."""
        result = benchmark(get_company, "AAPL")
        assert len(result) == 1
        assert result[0]['ticker'] == 'AAPL'

    @pytest.mark.benchmark
    def test_search_performance(self, benchmark):
        """Benchmark search functionality."""
        result = benchmark(search_companies, "Apple", limit=5)
        assert len(result) >= 1

    @pytest.mark.benchmark
    def test_batch_lookup_performance(self, benchmark):
        """Benchmark batch CIK lookup performance."""
        ciks = [320193, 789019, 1652044]
        result = benchmark(get_companies_by_ciks, ciks)
        assert len(result) == 3

    def test_performance_targets(self):
        """Verify performance targets are met."""
        
        # Test cached lookup performance (should be < 1ms)
        start_time = time.perf_counter()
        for _ in range(100):
            get_company_by_ticker("AAPL")
        end_time = time.perf_counter()
        
        avg_time_ms = ((end_time - start_time) / 100) * 1000
        assert avg_time_ms < 1.0, f"Cached lookup took {avg_time_ms:.3f}ms, expected < 1ms"

    def test_memory_efficiency(self):
        """Test memory usage remains reasonable."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform many lookups
        for i in range(1000):
            get_company("AAPL")
            get_company(320193)
            search_companies("Apple", limit=1)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be minimal (< 10MB for 1000 operations)
        assert memory_growth < 10, f"Memory grew by {memory_growth:.1f}MB, expected < 10MB"

    def test_batch_processing_efficiency(self):
        """Test batch operations are more efficient than individual calls."""
        ciks = [320193, 789019, 1652044, 1018724] * 25  # 100 CIKs
        
        # Time individual lookups
        start_time = time.perf_counter()
        individual_results = []
        for cik in ciks:
            result = get_company_by_cik(cik)
            individual_results.extend(result)
        individual_time = time.perf_counter() - start_time
        
        # Time batch lookup
        start_time = time.perf_counter()
        batch_results = get_companies_by_ciks(ciks)
        batch_time = time.perf_counter() - start_time
        
        # Batch should be significantly faster
        efficiency_ratio = individual_time / batch_time
        assert efficiency_ratio > 2.0, f"Batch processing only {efficiency_ratio:.1f}x faster, expected >2x"

    @pytest.mark.benchmark
    def test_concurrent_access_simulation(self, benchmark):
        """Simulate concurrent access patterns."""
        
        def mixed_operations():
            """Simulate mixed read operations."""
            get_company("AAPL")
            get_company_by_cik(789019)
            search_companies("tech", limit=3)
            get_companies_by_ciks([320193, 789019])
        
        result = benchmark(mixed_operations)

    def test_cache_warming_performance(self):
        """Test cache warming performance."""
        # Clear cache
        global _memory_cache
        _memory_cache.clear()
        
        # Time cache warming
        start_time = time.perf_counter()
        _memory_cache.update(SAMPLE_SEC_DATA_CACHE)
        cache_warm_time = time.perf_counter() - start_time
        
        # Cache warming should be very fast (< 10ms for sample data)
        cache_warm_ms = cache_warm_time * 1000
        assert cache_warm_ms < 10, f"Cache warming took {cache_warm_ms:.3f}ms, expected < 10ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])