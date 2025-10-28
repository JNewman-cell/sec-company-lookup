"""
Advanced usage examples for the secmap package.
"""

from secmap import get_company, get_company_by_cik, get_cache_info, clear_cache, search_companies
import json

def cache_management():
    """Demonstrate cache management features."""
    print("=== Cache Management ===")
    
    # Get cache information
    cache_info = get_cache_info()
    print("Cache Info:")
    print(json.dumps(cache_info, indent=2, default=str))
    
    # Check if cache is expired
    if cache_info['cache_expired']:
        print("\nCache is expired, consider updating data")
    else:
        print(f"\nCache is fresh (updated {cache_info['cache_age_hours']:.1f} hours ago)")

def data_analysis_workflow():
    """Example of using secmap in a data analysis workflow."""
    print("\n=== Data Analysis Workflow ===")
    
    # Sample dataset with mixed identifiers
    portfolio = [
        "AAPL",          # Ticker
        "320193",        # CIK as string
        789019,          # CIK as int
        "Microsoft",     # Partial company name
        "Tesla, Inc.",   # Full company name
        "INVALID"        # Invalid identifier
    ]
    
    print("Processing portfolio with mixed identifiers:")
    
    enriched_data = []
    for identifier in portfolio:
        company = get_company(identifier)
        
        if company:
            enriched_data.append({
                'original_input': identifier,
                'ticker': company['ticker'],
                'cik': company['cik'],
                'company_name': company['name']
            })
            print(f"✓ {identifier} → {company['ticker']} ({company['name']})")
        else:
            print(f"✗ {identifier} → Not found")
    
    print(f"\nEnriched {len(enriched_data)} out of {len(portfolio)} entries")
    return enriched_data

def sector_analysis():
    """Example of finding companies in a specific sector."""
    print("\n=== Sector Analysis Example ===")
    
    # Search for technology companies
    tech_keywords = ["Apple", "Microsoft", "Google", "Amazon", "Meta", "Tesla"]
    
    tech_companies = []
    for keyword in tech_keywords:
        results = search_companies(keyword, limit=3)
        tech_companies.extend(results)
    
    # Remove duplicates based on CIK
    unique_companies = {}
    for company in tech_companies:
        unique_companies[company['cik']] = company
    
    print(f"Found {len(unique_companies)} unique technology companies:")
    for company in sorted(unique_companies.values(), key=lambda x: x['ticker']):
        print(f"  {company['ticker']:6} | CIK: {company['cik']:8} | {company['name']}")

def compliance_lookup():
    """Example for compliance/regulatory use cases."""
    print("\n=== Compliance Lookup Example ===")
    
    # Sample regulatory filings data (CIK identifiers)
    filing_ciks = [320193, 789019, 1652044, 1018724, 1045810]
    
    print("Converting CIK identifiers to readable company information:")
    
    compliance_report = []
    for cik in filing_ciks:
        company = get_company_by_cik(cik)
        
        if company:
            compliance_report.append({
                'cik': cik,
                'ticker': company['ticker'],
                'company_name': company['name'],
                'status': 'Found'
            })
            print(f"CIK {cik:8} → {company['ticker']:6} | {company['name']}")
        else:
            compliance_report.append({
                'cik': cik,
                'ticker': None,
                'company_name': None,
                'status': 'Not Found'
            })
            print(f"CIK {cik:8} → Not found in SEC database")
    
    return compliance_report

def error_handling_example():
    """Demonstrate error handling and edge cases."""
    print("\n=== Error Handling Examples ===")
    
    test_cases = [
        "",              # Empty string
        "   ",          # Whitespace
        "INVALID123",   # Invalid ticker
        "0000000000",   # Invalid CIK
        "123abc",       # Mixed alphanumeric
        None,           # None value
    ]
    
    print("Testing edge cases and invalid inputs:")
    
    for test_case in test_cases:
        try:
            result = get_company(test_case)
            status = "Found" if result else "Not found"
            print(f"  {repr(test_case):15} → {status}")
        except Exception as e:
            print(f"  {repr(test_case):15} → Error: {e}")

if __name__ == "__main__":
    cache_management()
    data_analysis_workflow()
    sector_analysis()
    compliance_lookup()
    error_handling_example()