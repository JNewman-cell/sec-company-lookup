# Security Policy

## Supported Versions

We actively support the following versions of secmap with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting Security Vulnerabilities

**Please do not report security vulnerabilities through public GitHub issues.**

### How to Report

Send security vulnerability reports to: **jpnewman167@gmail.com**

Include the following information in your report:

1. **Description** of the vulnerability
2. **Steps to reproduce** the issue
3. **Potential impact** assessment
4. **Affected versions** (if known)
5. **Suggested fix** (if you have one)
6. **Your contact information** for follow-up

### What to Expect

- **Acknowledgment** within 24 hours of receipt
- **Initial assessment** within 72 hours
- **Regular updates** on our investigation progress
- **Coordinated disclosure** timeline discussion

### Security Update Process

1. **Verify** the reported vulnerability
2. **Develop** a fix with comprehensive testing
3. **Prepare** security advisory and release notes
4. **Coordinate** disclosure with reporter
5. **Release** patched version
6. **Publish** security advisory

## Security Best Practices for Users

### Production Deployment

- **Keep dependencies updated** to latest secure versions
- **Monitor security advisories** for secmap and dependencies
- **Use environment variables** for sensitive configuration
- **Implement proper logging** for security monitoring
- **Follow least privilege principles** for application access

### Configuration Security

```python
# Use environment variables for sensitive settings
import os
user_agent = os.getenv('SECMAP_USER_AGENT', 'default-agent')

# Implement proper error handling to avoid information disclosure
try:
    result = secmap.get_company(identifier)
except Exception as e:
    logger.error(f"Lookup failed: {type(e).__name__}")  # Don't log sensitive data
    return {"error": "Lookup failed"}
```

### Data Privacy

- **SEC data is public** — no personal or sensitive information
- **Cache files** contain only public company information
- **No authentication** required for SEC data access
- **No user data collection** by secmap library

## Known Security Considerations

### Network Requests
- All requests to SEC API use HTTPS
- User-Agent headers can be customized via environment variables
- Network timeouts are configured to prevent hanging connections
- No authentication credentials are transmitted

### Local Storage
- Cache files are stored in user's home directory (`~/.secmap/`)
- SQLite databases use standard file permissions
- No encryption of cached data (not required for public information)
- Cache cleanup functions available for secure deletion

### Input Validation
- All user inputs are validated and sanitized
- SQL injection prevention through parameterized queries
- No execution of user-provided code or commands
- Safe handling of malformed data from external sources

## Security Architecture

### Threat Model

**In Scope:**
- Input validation vulnerabilities
- SQL injection in database operations
- Network request security
- Local file system security
- Dependency vulnerabilities

**Out of Scope:**
- Physical access to local machine
- Social engineering attacks
- Network infrastructure security
- SEC.gov API security (external dependency)

### Security Controls

1. **Input Validation**
   - Type checking on all function parameters
   - Sanitization of search queries
   - CIK format validation and normalization

2. **Database Security**
   - Parameterized SQL queries prevent injection
   - No dynamic SQL generation from user input
   - Read-only operations for most database interactions

3. **Network Security**
   - HTTPS-only communication with SEC API
   - Request timeout configuration
   - Proper error handling for network failures

4. **File System Security**
   - Cache files created with appropriate permissions
   - No execution of external binaries
   - Safe temporary file handling

## Compliance

### Data Handling
- **Public Data Only** — SEC company information is publicly available
- **No PII Collection** — No personal or sensitive information processed
- **GDPR Compliance** — Not applicable (public data only)
- **SOC 2** — Not applicable (no service provider components)

### Industry Standards
- Following **OWASP** security guidelines
- Implementing **secure coding practices**
- Using **dependency scanning** for known vulnerabilities
- Maintaining **audit logs** for security-relevant events

## Contact Information

For security-related questions or concerns:

- **Email:** jpnewman167@gmail.com
- **PGP Key:** Available upon request
- **Response Time:** 24-48 hours for initial contact

For general support:
- **GitHub Issues:** https://github.com/JNewman-cell/secmap/issues
- **GitHub Discussions:** https://github.com/JNewman-cell/secmap/discussions