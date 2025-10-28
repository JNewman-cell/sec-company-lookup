# secmap Development Guide

## 🚀 Quick Development Setup

### Option 1: Local Development

```bash
# Clone and setup
git clone https://github.com/JNewman-cell/secmap.git
cd secmap

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
pip install -r requirements-dev.txt

# Verify installation
pytest tests/ -v
```

### Option 2: Docker Development

```bash
# Quick start with Docker
docker-compose -f docker-compose.dev.yml up secmap-dev

# Run benchmarks
docker-compose -f docker-compose.dev.yml up secmap-benchmark

# Interactive development
docker-compose -f docker-compose.dev.yml exec secmap-dev bash
```

## 🏗️ Architecture Overview

### Core Components

```
secmap/
├── secmap/
│   ├── __init__.py           # Public API exports
│   ├── secmap.py            # Main engine with multi-tier caching
│   ├── db/
│   │   ├── __init__.py      # Database API
│   │   └── db.py           # SQLite operations with FTS5
│   └── utils/
│       ├── __init__.py      # Utility API  
│       └── utils.py        # Data fetching and cache management
├── tests/
│   ├── test_secmap.py       # Core functionality tests
│   ├── db/test_db.py        # Database layer tests
│   └── utils/test_utils.py  # Utility function tests
├── examples/
│   ├── basic_usage.py       # Getting started examples
│   └── advanced_usage.py    # Performance and batch operations
└── .github/workflows/       # CI/CD automation
```

### Performance Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    secmap Engine                        │
├─────────────────────────────────────────────────────────┤
│  Smart Lookup Router (Auto-detection)                  │
├─────────────────────────────────────────────────────────┤
│  LRU Cache (1000 items) ────► ~0.1ms lookups           │
├─────────────────────────────────────────────────────────┤
│  Memory Index (Hash Tables) ────► ~0.5ms lookups       │
├─────────────────────────────────────────────────────────┤
│  SQLite + FTS5 (Persistent) ────► ~2-5ms lookups       │
├─────────────────────────────────────────────────────────┤
│  SEC API (Fallback) ────► ~200-500ms + caching         │
└─────────────────────────────────────────────────────────┘
```

## 🧪 Testing Strategy

### Test Categories

```bash
# Unit tests (fast, isolated)
pytest tests/test_secmap.py::TestSecmapCore -v

# Integration tests (realistic workflows)
pytest tests/test_secmap.py::TestIntegrationAndPerformance -v

# Database tests (SQLite operations)
pytest tests/db/ -v

# Utility tests (caching, data fetching)
pytest tests/utils/ -v

# Edge case and robustness tests
pytest tests/test_secmap.py::TestEdgeCases -v
```

### Performance Testing

```bash
# Benchmark critical paths
pytest tests/ -k "performance" -v --tb=short

# Memory usage profiling
python -m memory_profiler examples/advanced_usage.py

# Load testing simulation
pytest tests/test_secmap.py::TestIntegrationAndPerformance::test_concurrent_access -v
```

### Coverage Analysis

```bash
# Generate coverage report
pytest --cov=secmap --cov-report=html --cov-report=term-missing

# Coverage targets
# - Core functions: 100%
# - Edge cases: >90%
# - Error handling: >95%
```

## ⚡ Performance Optimization

### Profiling Tools

```bash
# Function-level profiling
python -m cProfile -s cumulative examples/basic_usage.py

# Line-by-line profiling  
pip install line_profiler
kernprof -l -v examples/advanced_usage.py

# Memory profiling
pip install memory_profiler
python -m memory_profiler examples/advanced_usage.py
```

### Benchmark Targets

| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| Cached lookup | <0.1ms | ~0.1ms | ✅ |
| Cold lookup | <5ms | ~2ms | ✅ |
| Data update | <3s | ~1.8s | ✅ |
| Memory usage | <50MB | ~30MB | ✅ |

## 🔧 Code Quality Standards

### Automated Checks

```bash
# Format code (required before commit)
black secmap/ tests/ examples/

# Lint code (zero warnings policy)
flake8 secmap/ tests/ examples/ --max-line-length=88

# Type checking (gradual typing)
mypy secmap/ --ignore-missing-imports

# Security scanning
pip install bandit
bandit -r secmap/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Manual run
pre-commit run --all-files
```

### Documentation Standards

```python
def search_companies(
    query: str, 
    limit: int = 10, 
    fuzzy: bool = True
) -> List[Dict[str, Any]]:
    """
    Search companies with comprehensive docstring.
    
    Performance: ~0.3ms cached, ~5ms cold start
    
    Args:
        query: Search term (ticker, CIK, or company name)
        limit: Maximum results (1-1000, default: 10)
        fuzzy: Enable fuzzy matching (default: True)
        
    Returns:
        List of company dictionaries sorted by relevance:
        [{'cik': int, 'ticker': str, 'name': str}, ...]
        
    Raises:
        ValueError: If limit is out of range or query is empty
        NetworkError: If SEC API is unavailable and no cache exists
        
    Example:
        >>> results = search_companies("tech companies", limit=5)
        >>> len(results) <= 5
        True
        >>> all('cik' in company for company in results)
        True
    """
```

## 📦 Build and Release Process

### Version Management

```bash
# Update version in multiple files
# - pyproject.toml
# - setup.py  
# - secmap/__init__.py
# - CHANGELOG.md

# Version format: MAJOR.MINOR.PATCH (semver)
```

### Build Process

```bash
# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build package
python -m build

# Verify package integrity
twine check dist/*

# Test installation
pip install dist/secmap-*.whl
python -c "import secmap; print(secmap.__version__)"
```

### Release Checklist

- [ ] All tests pass (`pytest`)
- [ ] Code formatted (`black --check`)
- [ ] No lint warnings (`flake8`)
- [ ] Type checking passes (`mypy`)
- [ ] Documentation updated
- [ ] Version bumped consistently
- [ ] CHANGELOG.md updated
- [ ] Performance benchmarks meet targets
- [ ] Security scan clean (`bandit`)

### Deployment

```bash
# Test on TestPyPI first
twine upload --repository testpypi dist/*

# Verify test installation
pip install --index-url https://test.pypi.org/simple/ secmap

# Production release
twine upload dist/*

# Create GitHub release
git tag v0.1.1
git push origin v0.1.1
```

## 🐛 Debugging Guide

### Common Issues

**Cache not updating:**
```python
import secmap
info = secmap.get_cache_info()
print(f"Cache expired: {info['cache_expired']}")
print(f"Last update: {info['last_update']}")
secmap.clear_cache()
secmap.update_data()
```

**Performance regression:**
```bash
# Run benchmarks
pytest tests/ -k "performance" --benchmark-compare

# Profile specific function
python -c "
import cProfile, secmap
pr = cProfile.Profile()
pr.enable()
secmap.get_company('AAPL')
pr.disable()
pr.print_stats(sort='cumulative')
"
```

**Memory leaks:**
```bash
# Monitor memory usage
python -c "
import psutil, os, secmap
process = psutil.Process(os.getpid())
print(f'Memory before: {process.memory_info().rss / 1024 / 1024:.1f}MB')
for i in range(1000):
    secmap.get_company('AAPL')
print(f'Memory after: {process.memory_info().rss / 1024 / 1024:.1f}MB')
"
```

## 🤝 Contributing Workflow

### Feature Development

```bash
# Create feature branch
git checkout -b feature/performance-optimization

# Make changes with tests
# ... development work ...

# Run full test suite
pytest tests/ -v

# Check code quality
black . && flake8 . && mypy secmap/

# Commit with conventional commits
git commit -m "feat: add batch processing optimization

- Implement vectorized operations for CIK lookups
- Reduce memory allocation by 40%  
- Add comprehensive benchmarks
- Update documentation with performance metrics

Closes #123"

# Push and create PR
git push origin feature/performance-optimization
```

### Code Review Process

1. **Automated checks** must pass (CI/CD pipeline)
2. **Manual review** by maintainer
3. **Performance impact** assessment
4. **Documentation review** for API changes
5. **Backwards compatibility** verification

## 📊 Monitoring and Metrics

### Development Metrics

```bash
# Code complexity
radon cc secmap/ -a

# Technical debt
python -m pylint secmap/ --exit-zero

# Test coverage trends
pytest --cov=secmap --cov-report=json
```

### Performance Monitoring

Track these metrics during development:

- **Lookup latency** (P50, P95, P99)
- **Memory usage** (RSS, heap size)
- **Cache hit rates** (LRU, memory, database)
- **Error rates** (by exception type)
- **Build times** (CI/CD pipeline duration)

This comprehensive development setup ensures high code quality, performance, and maintainability for the secmap project.