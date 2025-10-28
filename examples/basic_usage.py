"""
Basic usage examples for the secmap package.
"""

from secmap import (
    get_company,
    get_company_by_ticker,
    get_company_by_cik,
    get_company_by_name,
    update_data,
    search_companies,
)


def basic_usage():
    """Basic usage examples."""
    print("=== Basic Usage Examples ===")

    # Update data (download latest SEC data)
    print("Updating SEC data...")
    success = update_data()
    print(f"Update successful: {success}")

    # Look up by ticker
    print("\n--- Lookup by Ticker ---")
    company = get_company_by_ticker("AAPL")
    print(f"AAPL: {company}")

    # Look up by CIK
    print("\n--- Lookup by CIK ---")
    company = get_company_by_cik(320193)
    print(f"CIK 320193: {company}")

    # Look up by company name
    print("\n--- Lookup by Company Name ---")
    company = get_company_by_name("Apple Inc.")
    print(f"Apple Inc.: {company}")

    # Smart lookup (auto-detects type)
    print("\n--- Smart Lookup ---")
    examples = ["MSFT", "789019", "Microsoft Corporation"]
    for example in examples:
        company = get_company(example)
        print(f"'{example}': {company}")


def search_example():
    """Search functionality example."""
    print("\n=== Search Examples ===")

    # Search for companies
    results = search_companies("Apple", limit=5)
    print(f"Search for 'Apple': {len(results)} results")
    for result in results:
        print(f"  {result}")

    results = search_companies("GOOG", limit=3)
    print(f"\nSearch for 'GOOG': {len(results)} results")
    for result in results:
        print(f"  {result}")


def batch_lookup_example():
    """Example of batch lookups."""
    print("\n=== Batch Lookup Example ===")

    # List of tickers to look up
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    print(f"Looking up {len(tickers)} companies...")
    results = []

    for ticker in tickers:
        company = get_company_by_ticker(ticker)
        if company:
            results.append(company)
            print(f"  {ticker}: {company['name']} (CIK: {company['cik']})")
        else:
            print(f"  {ticker}: Not found")

    print(f"\nFound {len(results)} out of {len(tickers)} companies")


def performance_example():
    """Demonstrate performance with repeated lookups."""
    print("\n=== Performance Example ===")

    import time

    # Warm up cache
    get_company_by_ticker("AAPL")

    # Time repeated lookups
    start_time = time.time()
    iterations = 1000

    for _ in range(iterations):
        get_company_by_ticker("AAPL")
        get_company_by_cik(320193)
        get_company("Microsoft Corporation")

    end_time = time.time()
    total_time = end_time - start_time
    avg_time = (total_time / (iterations * 3)) * 1000  # Convert to milliseconds

    print(f"Performed {iterations * 3} lookups in {total_time:.4f} seconds")
    print(f"Average lookup time: {avg_time:.4f} ms")


if __name__ == "__main__":
    basic_usage()
    search_example()
    batch_lookup_example()
    performance_example()
