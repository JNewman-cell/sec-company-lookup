"""
Configuration management for sec-company-lookup package.

This module handles user configuration including email settings for SEC API compliance.
"""

import os
import re
from typing import Optional

# Global configuration
_user_email: Optional[str] = None


def set_user_email(email: str) -> None:
    """
    Set the user email for SEC API requests.

    Args:
        email: User's email address for SEC fair access policy compliance

    Raises:
        ValueError: If email format is invalid

    Example:
        >>> from sec_company_lookup.config import set_user_email
        >>> set_user_email("user@example.com")
    """
    global _user_email

    # Basic validation
    if "@" not in email:
        raise ValueError("Invalid email: must contain '@' symbol")

    # More thorough email validation
    pattern = r"^[^@]+@[^@]+\.[^@]+$"
    if not re.match(pattern, email):
        raise ValueError("Invalid email format")

    _user_email = email


def get_user_email() -> Optional[str]:
    """
    Get the configured user email.

    Checks in order:
    1. Email set via set_user_email()
    2. SECCOMPANYLOOKUP_USER_EMAIL environment variable

    Returns:
        str: User email if configured, None otherwise
    """
    # First check if email was set via function
    if _user_email:
        return _user_email

    # Fallback to environment variable
    env_email = os.getenv("SECCOMPANYLOOKUP_USER_EMAIL")
    if env_email:
        try:
            # Validate the environment email
            set_user_email(env_email)
            return env_email
        except ValueError:
            # Invalid email in environment variable, ignore it
            pass

    return None


def get_user_agent() -> str:
    """
    Generate User-Agent string for SEC API requests.

    Returns:
        str: Properly formatted User-Agent string

    Raises:
        ValueError: If no email is configured
    """
    email = get_user_email()
    if not email:
        raise ValueError(
            "User email is required for SEC API requests. "
            "Set it using:\n"
            "1. sec_company_lookup.set_user_email('your@email.com'), or\n"
            "2. Set SECCOMPANYLOOKUP_USER_EMAIL environment variable"
        )

    return f"sec-company-lookup/0.1.0 ({email})"


def clear_user_email() -> None:
    """Clear the configured user email."""
    global _user_email
    _user_email = None
