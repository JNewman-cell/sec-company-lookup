<!-- markdownlint-disable MD041 -->
# Contributing to secmap

Thank you for your interest in contributing to secmap! This guide will help you get started with contributing to this high-performance SEC data lookup library.

## 🚀 Quick Start for Contributors

### Development Environment Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/secmap.git
   cd secmap
   ```

2. **Setup Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -e .
   pip install -r requirements-dev.txt
   ```

4. **Verify Installation**
   ```bash
   pytest tests/ -v
   ```

## 🎯 Areas for Contribution

### High Priority
- **Performance Optimizations** — Caching strategies, memory efficiency
- **Search Improvements** — Better fuzzy matching algorithms
- **Error Handling** — Edge cases, network resilience
- **Documentation** — API examples, architecture guides

### Medium Priority  
- **Additional Data Sources** — International exchanges, EDGAR integration
- **API Extensions** — New search methods, filtering options
- **Testing** — Performance benchmarks, integration tests
- **Tooling** — CI/CD improvements, automated benchmarks

### Low Priority
- **Code Quality** — Type hints, docstring improvements
- **Examples** — Real-world use cases, tutorials
- **Packaging** — Distribution optimizations

## 🔧 Development Guidelines

### Code Quality Standards

#### Formatting & Style
```bash
# Format code with Black (88 char line limit)
black secmap/ tests/ examples/

# Lint with flake8
flake8 secmap/ tests/ examples/

# Type checking with mypy
mypy secmap/
```

#### Testing Requirements
- **All new features** must include comprehensive tests
- **Maintain >95% coverage** on critical paths
- **Include performance tests** for optimization changes
- **Test edge cases** thoroughly

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=secmap --cov-report=html

# Run performance tests
pytest tests/test_performance.py -v
```

### Coding Conventions

#### Function/Method Design
```python
def search_companies(
    query: str, 
    limit: int = 10, 
    fuzzy: bool = True
) -> List[Dict[str, Any]]:
    """
    Search for companies with comprehensive docstring.
    
    Args:
        query: Search term for company lookup
        limit: Maximum number of results (default: 10)
        fuzzy: Enable fuzzy matching (default: True)
        
    Returns:
        List of company dictionaries with cik, ticker, name
        
    Raises:
        ValueError: If query is empty or limit is invalid
        
    Example:
        >>> results = search_companies("apple", limit=5)
        >>> len(results) <= 5
        True
    """
```

#### Error Handling
```python
# Prefer specific exceptions
raise ValueError(f"Invalid CIK format: {cik}")

# Include context in error messages  
logger.error(f"Failed to download SEC data: {e}")

# Graceful degradation
try:
    return search_companies_db(query, limit, fuzzy)
except DatabaseError:
    logger.warning("Database unavailable, falling back to memory search")
    return search_companies_memory(query, limit, fuzzy)
```

### Performance Considerations

#### Memory Efficiency
- Use generators for large datasets
- Implement proper cleanup in finally blocks
- Profile memory usage for optimization changes

#### Caching Strategy
- Understand the multi-tier cache architecture
- Consider cache invalidation implications
- Test performance with realistic datasets

## 🧪 Testing Strategy

### Test Categories

#### Unit Tests (`tests/test_*.py`)
```python
def test_get_company_by_ticker():
    """Test core ticker lookup functionality."""
    with patch('secmap.secmap._memory_cache', SAMPLE_SEC_DATA_CACHE):
        result = get_company_by_ticker("AAPL")
        assert result[0]['ticker'] == "AAPL"
        assert result[0]['cik'] == 320193
```

#### Integration Tests (`tests/test_integration.py`)
```python
def test_full_workflow_integration():
    """Test complete workflow from data download to lookup."""
    # Test realistic usage patterns
    pass
```

#### Performance Tests (`tests/test_performance.py`)
```python
def test_lookup_performance():
    """Ensure sub-millisecond performance targets."""
    # Benchmark critical paths
    pass
```

### Test Data Management
- Use `SAMPLE_SEC_DATA` fixture for consistent testing
- Mock external API calls to avoid network dependencies
- Test with realistic data volumes

## 📋 Pull Request Process

### Before Submitting
1. ✅ **All tests pass** locally
2. ✅ **Code is formatted** with Black
3. ✅ **No linting errors** from flake8
4. ✅ **Type checking passes** with mypy
5. ✅ **Documentation updated** if needed

### PR Requirements
- **Clear description** of changes and motivation
- **Link to related issues** using `Fixes #123` syntax
- **Include tests** for new functionality
- **Update documentation** for API changes
- **Performance impact** assessment for optimizations

### PR Template
```markdown
## Description
Brief description of changes and why they're needed.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)  
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Performance improvement
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Performance tests added/updated
- [ ] All tests pass locally

## Performance Impact
Describe any performance implications of these changes.

## Documentation
- [ ] Docstrings updated
- [ ] README updated if needed
- [ ] Examples updated if needed
```

## 🔒 Security Guidelines

### Reporting Security Issues
**Do not create public GitHub issues for security vulnerabilities.**

Email security issues to: jpnewman167@gmail.com

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if known)

### Security Best Practices
- Validate all user inputs
- Use parameterized queries for database operations
- Handle API keys and credentials securely
- Follow OWASP guidelines for web application security

## 🏆 Recognition

Contributors are recognized in several ways:
- **GitHub Contributors Graph** — Automatic recognition
- **Release Notes** — Major contributions highlighted
- **Documentation** — Contributors section in README
- **Recommendations** — LinkedIn endorsements for significant contributions

## 📞 Getting Help

### Communication Channels
- **GitHub Issues** — Bug reports, feature requests
- **GitHub Discussions** — Design discussions, questions
- **Email** — jpnewman167@gmail.com for urgent matters

### Mentorship
New contributors can request mentorship for:
- Understanding the codebase architecture
- Guidance on specific features
- Code review feedback
- Career development advice

## 🎉 Thank You!

Every contribution makes secmap better for the entire financial Python community. Whether it's a typo fix, performance optimization, or major feature addition — we appreciate your effort!