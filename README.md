# sec-company-lookup

[![Tests](https://github.com/JNewman-cell/sec-company-lookup/workflows/tests/badge.svg)](https://github.com/JNewman-cell/sec-company-lookup/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Fast, cached SEC company lookups by ticker, CIK, or company name with automatic data updates and multi-level caching.

## Installation

```bash
pip install sec-company-lookup
```

## Quick Start

```python
from sec_company_lookup import set_user_email, get_company

# Configure email for SEC API compliance (required)
set_user_email("your@email.com")

# Smart lookup - auto-detects ticker, CIK, or company name
companies = get_company("AAPL")           # By ticker
companies = get_company(320193)           # By CIK
companies = get_company("Apple")          # By name (fuzzy)

print(companies)
# [{'cik': 320193, 'ticker': 'AAPL', 'name': 'Apple Inc.'}]
```

## Core Features

- **Smart lookup** - Auto-detects ticker, CIK, or company name
- **Fast caching** - Multi-tier caching (memory + SQLite + LRU)
- **Fuzzy search** - Find companies with partial names
- **Batch operations** - Process multiple lookups efficiently
- **Auto-updates** - Downloads latest SEC data when needed

## Email Configuration

The SEC requires contact information. Configure using any method:

```python
# Method 1: In code (recommended)
from sec_company_lookup import set_user_email
set_user_email("your@email.com")

# Method 2: Environment variable
# export SECCOMPANYLOOKUP_USER_EMAIL="your@email.com"
```

## API Functions

### Core Lookup Functions

```python
from sec_company_lookup import (
    get_company,                # Smart lookup (auto-detects input type)
    get_companies_by_tickers,   # Lookup by ticker(s) - single or batch
    get_companies_by_ciks,      # Lookup by CIK(s) - single or batch
    get_companies_by_names,     # Lookup by name(s) - single or batch
)

# Single lookups
company = get_company("AAPL")                           # Auto-detect (returns list)
company = get_companies_by_tickers("MSFT")              # By ticker (returns CompanyData or None)
companies = get_companies_by_ciks(789019)               # By CIK (returns list)
company = get_companies_by_names("Apple", fuzzy=True)   # By name (returns CompanyData or None)

# Batch lookups
results = get_companies_by_tickers(["AAPL", "MSFT"])    # Returns dict with structured responses
results = get_companies_by_ciks([320193, 789019])       # Returns dict mapping CIK to list
results = get_companies_by_names(["Apple", "Microsoft"])  # Returns dict with structured responses
```

### Search Functions

```python
from sec_company_lookup import (
    search_companies,                    # General search across all fields
    search_companies_by_company_name,    # Company name specific search
)

# Examples  
results = search_companies("tech", limit=10)
results = search_companies_by_company_name("Apple", fuzzy=True, limit=5)
```

### Batch Operations

```python
from sec_company_lookup import (
    get_companies_by_tickers,   # Batch ticker lookup
    get_companies_by_ciks,      # Batch CIK lookup
    get_companies_by_names,     # Batch name lookup
)

# Batch ticker lookup
tickers = ["AAPL", "MSFT", "GOOGL"]
results = get_companies_by_tickers(tickers)
# Returns: {
#   "AAPL": {"success": True, "data": {...}},
#   "MSFT": {"success": True, "data": {...}},
#   "GOOGL": {"success": True, "data": {...}}
# }

# Batch CIK lookup (CIKs can map to multiple companies)
ciks = [320193, 789019, 1652044]
results = get_companies_by_ciks(ciks)
# Returns: {
#   320193: {"success": True, "data": [...]},
#   789019: {"success": True, "data": [...]},
#   1652044: {"success": True, "data": [...]}
# }

# Batch name lookup
names = ["Apple Inc.", "Microsoft Corporation"]
results = get_companies_by_names(names, fuzzy=True)
# Returns: {
#   "Apple Inc.": {"success": True, "data": {...}},
#   "Microsoft Corporation": {"success": True, "data": {...}}
# }
```

### Cache Management

```python
from sec_company_lookup import update_data, clear_cache, get_cache_info

# Force update from SEC
update_data()

# Check cache status
info = get_cache_info()
print(f"Companies cached: {info['companies_cached']}")
print(f"Cache age: {info['cache_age_hours']:.1f} hours")

# Clear all caches
clear_cache()
```

## Data Structure

Each company record contains:

```python
{
    'cik': 320193,           # SEC Central Index Key (integer)
    'ticker': 'AAPL',        # Stock ticker symbol  
    'name': 'Apple Inc.'     # Official company name
}
```

## Performance

Multi-tier caching provides fast lookups:

- **Memory cache**: < 1ms
- **Database lookup**: 1-5ms  
- **Initial download**: ~2 seconds

## Package Structure

```
sec_company_lookup/
├── __init__.py                  # Main package entry point
├── sec_company_lookup.py        # Core backend implementation
├── config.py                    # Email configuration
├── api/
│   ├── __init__.py
│   └── api.py                   # Public API layer
├── db/
│   ├── __init__.py
│   └── db.py                    # SQLite database operations
├── types/
│   ├── __init__.py
│   └── types.py                 # Type definitions
└── utils/
    ├── __init__.py
    └── utils.py                 # Utility functions & data fetching
```

## License

MIT License - see [LICENSE](LICENSE) file for details.