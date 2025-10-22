"""
Privacy utilities for sanitizing PII from telemetry data.

Provides functions to detect and sanitize personally identifiable information
including phone numbers, emails, API keys, and other sensitive data.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Literal

# Type alias for sanitization strategies
SanitizationStrategy = Literal["hash", "redact", "truncate"]


@dataclass
class PrivacyConfig:
    """
    Configuration for privacy utilities.

    Attributes:
        strategy: Sanitization strategy to use (hash, redact, or truncate)
        max_string_length: Maximum length for strings before truncation
        redaction_text: Text to use when redacting sensitive data
    """

    strategy: SanitizationStrategy = "hash"
    max_string_length: int = 1000
    redaction_text: str = "[REDACTED]"


# Default configuration instance
DEFAULT_CONFIG = PrivacyConfig()


# PII detection patterns
class Patterns:
    """Regular expression patterns for detecting PII."""

    # Phone: matches international formats like +1-555-555-5555, (555) 555-5555, 555.555.5555
    PHONE = re.compile(
        r"(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})|"
        r"(\+?[0-9]{1,3}[-.\s]?)?(\([0-9]{2,4}\)|[0-9]{2,4})[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{4}"
    )

    # Email: standard email pattern
    EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

    # API keys: patterns like xxx-xxx-xxx, sk_live_xxx, Bearer xxx
    API_KEY = re.compile(
        r"\b(sk_live_|sk_test_|pk_live_|pk_test_|Bearer\s+|api[_-]?key[_-]?)[a-zA-Z0-9_-]{20,}\b",
        re.IGNORECASE,
    )

    # Credit card: basic pattern (not perfect, but catches most)
    CREDIT_CARD = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")

    # IPv4 addresses
    IPV4 = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

    # File paths with user info (Unix and Windows)
    USER_PATH = re.compile(
        r"/(?:home|Users)/[a-zA-Z0-9_-]+|[A-Z]:\\Users\\[a-zA-Z0-9_-]+", re.IGNORECASE
    )


def hash_value(value: str) -> str:
    """
    Hash a value using SHA-256.
    Returns a truncated hash for readability while maintaining uniqueness.

    Args:
        value: The string to hash

    Returns:
        A string in the format 'sha256:' followed by first 16 chars of hash

    Example:
        >>> hash_value('sensitive-data')
        'sha256:a1b2c3d4...'
    """
    hash_obj = hashlib.sha256(value.encode("utf-8"))
    hash_hex = hash_obj.hexdigest()
    return f"sha256:{hash_hex[:16]}"


def detect_pii(value: str) -> bool:
    """
    Detect if a value contains potential PII.

    Args:
        value: The string to check for PII

    Returns:
        True if PII is detected, False otherwise

    Example:
        >>> detect_pii('user@example.com')
        True
        >>> detect_pii('Hello world')
        False
    """
    if not isinstance(value, str):
        return False

    patterns = [
        Patterns.PHONE,
        Patterns.EMAIL,
        Patterns.API_KEY,
        Patterns.CREDIT_CARD,
        Patterns.IPV4,
        Patterns.USER_PATH,
    ]

    return any(pattern.search(value) for pattern in patterns)


def sanitize_phone(value: str, config: PrivacyConfig | None = None) -> str:
    """
    Sanitize a phone number.

    Args:
        value: The string potentially containing phone numbers
        config: Privacy configuration to use (defaults to DEFAULT_CONFIG)

    Returns:
        The sanitized string

    Example:
        >>> sanitize_phone('+1-555-555-5555', PrivacyConfig(strategy='hash'))
        'sha256:a1b2c3d4...'
        >>> sanitize_phone('(555) 555-5555', PrivacyConfig(strategy='redact'))
        '[REDACTED]'
    """
    cfg = config or DEFAULT_CONFIG

    if not Patterns.PHONE.search(value):
        return value

    if cfg.strategy == "hash":
        return Patterns.PHONE.sub(lambda m: hash_value(m.group(0)), value)
    elif cfg.strategy == "redact":
        return Patterns.PHONE.sub(cfg.redaction_text, value)
    elif cfg.strategy == "truncate":
        return Patterns.PHONE.sub("XXX-XXX-XXXX", value)
    else:
        return value


def sanitize_email(value: str, config: PrivacyConfig | None = None) -> str:
    """
    Sanitize an email address.

    Args:
        value: The string potentially containing email addresses
        config: Privacy configuration to use (defaults to DEFAULT_CONFIG)

    Returns:
        The sanitized string

    Example:
        >>> sanitize_email('user@example.com', PrivacyConfig(strategy='hash'))
        'sha256:a1b2c3d4...'
        >>> sanitize_email('test@test.com', PrivacyConfig(strategy='redact'))
        '[REDACTED]'
        >>> sanitize_email('user@example.com', PrivacyConfig(strategy='truncate'))
        'us***@example.com'
    """
    cfg = config or DEFAULT_CONFIG

    if not Patterns.EMAIL.search(value):
        return value

    if cfg.strategy == "hash":
        return Patterns.EMAIL.sub(lambda m: hash_value(m.group(0)), value)
    elif cfg.strategy == "redact":
        return Patterns.EMAIL.sub(cfg.redaction_text, value)
    elif cfg.strategy == "truncate":

        def truncate_email(match: re.Match[str]) -> str:
            email = match.group(0)
            if "@" in email:
                user, domain = email.split("@", 1)
                return f"{user[:2]}***@{domain}"
            return email

        result: str = Patterns.EMAIL.sub(truncate_email, value)
        return result
    else:
        return value


def truncate_string(value: str, max_length: int) -> str:
    """
    Truncate a string to a maximum length.

    Args:
        value: The string to truncate
        max_length: Maximum allowed length

    Returns:
        The truncated string with '...' appended if it was too long

    Example:
        >>> truncate_string('Very long string...', 10)
        'Very lon...'
    """
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."


def sanitize_value(value: Any, config: PrivacyConfig | None = None) -> Any:
    """
    Auto-sanitize a value based on PII detection.
    Handles strings, numbers, objects, and arrays recursively.

    Args:
        value: The value to sanitize (can be any type)
        config: Privacy configuration to use (defaults to DEFAULT_CONFIG)

    Returns:
        The sanitized value (same type as input)

    Example:
        >>> sanitize_value('Contact: user@example.com')
        'Contact: sha256:a1b2c3d4...'
        >>> sanitize_value({'email': 'test@test.com', 'phone': '555-555-5555'})
        {'email': 'sha256:...', 'phone': 'sha256:...'}
    """
    cfg = config or DEFAULT_CONFIG

    # Handle None
    if value is None:
        return value

    # Handle strings
    if isinstance(value, str):
        # Truncate if too long
        sanitized = truncate_string(value, cfg.max_string_length)

        # Apply pattern-based sanitization
        if Patterns.PHONE.search(sanitized):
            sanitized = sanitize_phone(sanitized, config)
        if Patterns.EMAIL.search(sanitized):
            sanitized = sanitize_email(sanitized, config)
        if Patterns.API_KEY.search(sanitized):
            sanitized = Patterns.API_KEY.sub(cfg.redaction_text, sanitized)
        if Patterns.CREDIT_CARD.search(sanitized):
            sanitized = Patterns.CREDIT_CARD.sub(cfg.redaction_text, sanitized)
        if Patterns.IPV4.search(sanitized):
            if cfg.strategy == "hash":
                sanitized = Patterns.IPV4.sub(lambda m: hash_value(m.group(0)), sanitized)
            else:
                sanitized = Patterns.IPV4.sub("X.X.X.X", sanitized)
        if Patterns.USER_PATH.search(sanitized):
            sanitized = Patterns.USER_PATH.sub("/[USER_PATH]", sanitized)

        return sanitized

    # Handle numbers and booleans (pass through)
    if isinstance(value, (int, float, bool)):
        return value

    # Handle lists recursively
    if isinstance(value, list):
        return [sanitize_value(item, config) for item in value]

    # Handle dictionaries recursively
    if isinstance(value, dict):
        return {key: sanitize_value(val, config) for key, val in value.items()}

    # Pass through other types
    return value


def redact_sensitive_keys(
    obj: dict[str, Any], keys: list[str], config: PrivacyConfig | None = None
) -> dict[str, Any]:
    """
    Redact specific keys from an object.
    Useful for known sensitive fields like 'password', 'token', etc.

    Args:
        obj: The dictionary to process
        keys: List of sensitive key names to redact
        config: Privacy configuration to use (defaults to DEFAULT_CONFIG)

    Returns:
        A new dictionary with sensitive keys redacted

    Example:
        >>> data = {'username': 'john', 'password': 'secret123', 'token': 'abc'}
        >>> redact_sensitive_keys(data, ['password', 'token'])
        {'username': 'john', 'password': '[REDACTED]', 'token': '[REDACTED]'}
    """
    cfg = config or DEFAULT_CONFIG
    result: dict[str, Any] = {}

    for key, value in obj.items():
        # Check if key matches any sensitive key (case-insensitive substring match)
        if any(k.lower() in key.lower() for k in keys):
            result[key] = cfg.redaction_text
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            result[key] = redact_sensitive_keys(value, keys, config)
        else:
            result[key] = value

    return result


# Common sensitive key patterns to redact
SENSITIVE_KEYS = [
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "private_key",
    "credit_card",
    "ssn",
    "social_security",
]


def sanitize_telemetry_data(
    data: dict[str, Any], config: PrivacyConfig | None = None
) -> dict[str, Any]:
    """
    Sanitize telemetry data before sending.
    Combines multiple sanitization strategies for comprehensive privacy protection.

    Args:
        data: The telemetry data dictionary to sanitize
        config: Privacy configuration to use (defaults to DEFAULT_CONFIG)

    Returns:
        A new dictionary with all sensitive data sanitized

    Example:
        >>> data = {
        ...     'user': {'email': 'test@example.com', 'password': 'secret'},
        ...     'message': 'Error at /home/user/project/file.ts',
        ... }
        >>> sanitize_telemetry_data(data)
        {
            'user': {'email': 'sha256:...', 'password': '[REDACTED]'},
            'message': 'Error at /[USER_PATH]/project/file.ts',
        }
    """
    # First redact known sensitive keys
    sanitized = redact_sensitive_keys(data, SENSITIVE_KEYS, config)

    # Then apply pattern-based sanitization
    result: dict[str, Any] = sanitize_value(sanitized, config)  # type: ignore[assignment]

    return result
