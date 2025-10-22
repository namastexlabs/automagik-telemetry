"""
Comprehensive tests for privacy utilities.

Tests cover:
- PII detection (phone, email, API keys, credit cards, IPs, paths)
- Sanitization strategies (hash, redact, truncate)
- Phone number sanitization
- Email sanitization
- API key detection and redaction
- Credit card detection
- IP address sanitization
- User path sanitization
- Sensitive key redaction
- Telemetry data sanitization
- Recursive sanitization (nested objects and arrays)
"""

from automagik_telemetry.privacy import (
    DEFAULT_CONFIG,
    SENSITIVE_KEYS,
    Patterns,
    PrivacyConfig,
    detect_pii,
    hash_value,
    redact_sensitive_keys,
    sanitize_email,
    sanitize_phone,
    sanitize_telemetry_data,
    sanitize_value,
    truncate_string,
)


class TestHashValue:
    """Test value hashing functionality."""

    def test_should_hash_value_consistently(self) -> None:
        """Test that same value always produces same hash."""
        value = "test-value-123"
        hash1 = hash_value(value)
        hash2 = hash_value(value)

        assert hash1 == hash2

    def test_should_produce_different_hashes_for_different_values(self) -> None:
        """Test that different values produce different hashes."""
        hash1 = hash_value("value1")
        hash2 = hash_value("value2")

        assert hash1 != hash2

    def test_should_include_sha256_prefix(self) -> None:
        """Test that hash includes sha256: prefix."""
        result = hash_value("test")

        assert result.startswith("sha256:")

    def test_should_truncate_hash_to_16_chars(self) -> None:
        """Test that hash is truncated to 16 characters (plus prefix)."""
        result = hash_value("test")

        # sha256: (7 chars) + 16 hex chars = 23 total
        assert len(result) == 23


class TestDetectPII:
    """Test PII detection."""

    def test_should_detect_email(self) -> None:
        """Test detection of email addresses."""
        assert detect_pii("user@example.com") is True
        assert detect_pii("Contact: test@test.org") is True

    def test_should_detect_phone_numbers(self) -> None:
        """Test detection of phone numbers in various formats."""
        assert detect_pii("+1-555-555-5555") is True
        assert detect_pii("(555) 555-5555") is True
        assert detect_pii("555.555.5555") is True
        assert detect_pii("+44 20 7946 0958") is True

    def test_should_detect_api_keys(self) -> None:
        """Test detection of API keys."""
        assert detect_pii("sk_test_FAKE_KEY_NOT_REAL_12345678r") is True
        assert detect_pii("Bearer abc123def456ghi789jkl012mno345pqr") is True
        assert detect_pii("api_key_abc123def456ghi789jkl012mno345pqr") is True

    def test_should_detect_credit_cards(self) -> None:
        """Test detection of credit card numbers."""
        assert detect_pii("4532-1234-5678-9010") is True
        assert detect_pii("4532 1234 5678 9010") is True
        assert detect_pii("4532123456789010") is True

    def test_should_detect_ipv4_addresses(self) -> None:
        """Test detection of IPv4 addresses."""
        assert detect_pii("192.168.1.1") is True
        assert detect_pii("10.0.0.255") is True
        assert detect_pii("Server IP: 8.8.8.8") is True

    def test_should_detect_user_paths(self) -> None:
        """Test detection of file paths containing usernames."""
        assert detect_pii("/home/johndoe/project/file.py") is True
        assert detect_pii("C:\\Users\\johndoe\\Documents\\file.txt") is True

    def test_should_not_detect_pii_in_normal_text(self) -> None:
        """Test that normal text is not flagged as PII."""
        assert detect_pii("Hello world") is False
        assert detect_pii("The quick brown fox") is False
        assert detect_pii("Error code 404") is False

    def test_should_handle_non_string_values(self) -> None:
        """Test that non-string values return False."""
        assert detect_pii(123) is False
        assert detect_pii(None) is False
        assert detect_pii(True) is False


class TestSanitizePhone:
    """Test phone number sanitization."""

    def test_should_hash_phone_by_default(self) -> None:
        """Test that phone numbers are hashed by default."""
        result = sanitize_phone("+1-555-555-5555")

        assert result.startswith("sha256:")
        assert "+1-555-555-5555" not in result

    def test_should_redact_phone_with_redact_strategy(self) -> None:
        """Test phone redaction strategy."""
        config = PrivacyConfig(strategy="redact")
        result = sanitize_phone("(555) 555-5555", config)

        assert result == "[REDACTED]"

    def test_should_truncate_phone_with_truncate_strategy(self) -> None:
        """Test phone truncation strategy."""
        config = PrivacyConfig(strategy="truncate")
        result = sanitize_phone("555-555-5555", config)

        assert result == "XXX-XXX-XXXX"

    def test_should_preserve_non_phone_text(self) -> None:
        """Test that non-phone text is preserved."""
        result = sanitize_phone("Hello world")

        assert result == "Hello world"

    def test_should_sanitize_phone_in_context(self) -> None:
        """Test sanitizing phone number within a sentence."""
        config = PrivacyConfig(strategy="redact")
        result = sanitize_phone("Call me at (555) 555-5555 anytime", config)

        assert "(555) 555-5555" not in result
        assert "[REDACTED]" in result

    def test_should_use_custom_redaction_text(self) -> None:
        """Test using custom redaction text."""
        config = PrivacyConfig(strategy="redact", redaction_text="[HIDDEN]")
        result = sanitize_phone("555-555-5555", config)

        assert result == "[HIDDEN]"

    def test_should_handle_unknown_strategy(self) -> None:
        """Test that unknown strategy returns value unchanged."""
        config = PrivacyConfig(strategy="invalid")  # type: ignore
        result = sanitize_phone("555-555-5555", config)

        assert result == "555-555-5555"


class TestSanitizeEmail:
    """Test email sanitization."""

    def test_should_hash_email_by_default(self) -> None:
        """Test that emails are hashed by default."""
        result = sanitize_email("user@example.com")

        assert result.startswith("sha256:")
        assert "user@example.com" not in result

    def test_should_redact_email_with_redact_strategy(self) -> None:
        """Test email redaction strategy."""
        config = PrivacyConfig(strategy="redact")
        result = sanitize_email("user@example.com", config)

        assert result == "[REDACTED]"

    def test_should_truncate_email_with_truncate_strategy(self) -> None:
        """Test email truncation strategy."""
        config = PrivacyConfig(strategy="truncate")
        result = sanitize_email("user@example.com", config)

        assert result == "us***@example.com"

    def test_should_preserve_non_email_text(self) -> None:
        """Test that non-email text is preserved."""
        result = sanitize_email("Hello world")

        assert result == "Hello world"

    def test_should_sanitize_email_in_context(self) -> None:
        """Test sanitizing email within a sentence."""
        config = PrivacyConfig(strategy="redact")
        result = sanitize_email("Contact me at user@example.com", config)

        assert "user@example.com" not in result
        assert "[REDACTED]" in result

    def test_should_truncate_short_email_correctly(self) -> None:
        """Test truncating short email addresses."""
        config = PrivacyConfig(strategy="truncate")
        result = sanitize_email("a@example.com", config)

        assert result == "a***@example.com"

    def test_should_handle_malformed_email_in_truncate(self) -> None:
        """Test handling edge case in email truncation."""
        from unittest.mock import Mock, patch

        config = PrivacyConfig(strategy="truncate")

        # Mock the email pattern to match something without @ to test the edge case
        with patch("automagik_telemetry.privacy.Patterns.EMAIL") as mock_pattern:
            mock_match = Mock()
            mock_match.group.return_value = "notanemail"  # No @ symbol
            mock_pattern.search.return_value = mock_match
            mock_pattern.sub.side_effect = lambda func, val: func(mock_match)

            # This will trigger the "return email" branch when @ not in email
            result = sanitize_email("test string", config)

            assert result == "notanemail"

    def test_should_handle_unknown_email_strategy(self) -> None:
        """Test that unknown strategy returns value unchanged for email."""
        config = PrivacyConfig(strategy="invalid")  # type: ignore
        result = sanitize_email("user@example.com", config)

        assert result == "user@example.com"


class TestTruncateString:
    """Test string truncation."""

    def test_should_not_truncate_short_strings(self) -> None:
        """Test that strings shorter than max length are not truncated."""
        result = truncate_string("Hello", 10)

        assert result == "Hello"

    def test_should_truncate_long_strings(self) -> None:
        """Test that long strings are truncated."""
        result = truncate_string("Hello world, this is a long string", 10)

        assert result == "Hello w..."
        assert len(result) == 10

    def test_should_add_ellipsis_to_truncated_strings(self) -> None:
        """Test that truncated strings end with ..."""
        result = truncate_string("Very long string", 10)

        assert result.endswith("...")

    def test_should_handle_exact_length(self) -> None:
        """Test string exactly at max length."""
        result = truncate_string("Hello", 5)

        assert result == "Hello"


class TestSanitizeValue:
    """Test general value sanitization."""

    def test_should_sanitize_string_with_email(self) -> None:
        """Test sanitizing string containing email."""
        result = sanitize_value("Contact: user@example.com")

        assert "user@example.com" not in result
        assert "sha256:" in result

    def test_should_sanitize_string_with_phone(self) -> None:
        """Test sanitizing string containing phone."""
        result = sanitize_value("Call: +1-555-555-5555")

        assert "+1-555-555-5555" not in result
        assert "sha256:" in result

    def test_should_sanitize_api_keys(self) -> None:
        """Test sanitizing API keys."""
        config = PrivacyConfig(strategy="redact")
        result = sanitize_value("Key: sk_test_FAKE_KEY_NOT_REAL_12345678r", config)

        assert "sk_live_" not in result
        assert "[REDACTED]" in result

    def test_should_sanitize_credit_cards(self) -> None:
        """Test sanitizing credit card numbers."""
        config = PrivacyConfig(strategy="redact")
        result = sanitize_value("Card: 4532-1234-5678-9010", config)

        assert "4532-1234-5678-9010" not in result
        assert "[REDACTED]" in result

    def test_should_sanitize_credit_card_standalone(self) -> None:
        """Test sanitizing credit card number alone."""
        config = PrivacyConfig(strategy="redact")
        # Use just the credit card to avoid phone pattern matching
        result = sanitize_value("4532123456789010", config)

        assert "4532123456789010" not in result
        assert "[REDACTED]" in result

    def test_should_sanitize_credit_card_without_phone_match(self) -> None:
        """Test credit card sanitization when phone pattern doesn't match."""
        from unittest.mock import patch

        config = PrivacyConfig(strategy="redact")

        # Mock PHONE.search to return None (no match) so we skip phone sanitization
        # This forces the code to reach the CREDIT_CARD check on line 247-248
        with patch("automagik_telemetry.privacy.Patterns.PHONE") as mock_phone_pattern:
            mock_phone_pattern.search.return_value = None

            # Test with a credit card number that would normally match both patterns
            result = sanitize_value("1111-2222-3333-4444", config)

            # The phone check should have been called but returned None
            assert mock_phone_pattern.search.called

            # The credit card should be redacted since phone didn't match
            assert "1111-2222-3333-4444" not in result
            assert "[REDACTED]" in result

    def test_should_sanitize_ip_addresses(self) -> None:
        """Test sanitizing IP addresses."""
        result = sanitize_value("Server: 192.168.1.100")

        assert "192.168.1.100" not in result

    def test_should_sanitize_user_paths(self) -> None:
        """Test sanitizing file paths with usernames."""
        result = sanitize_value("/home/johndoe/project/file.py")

        assert "/home/johndoe" not in result
        assert "/[USER_PATH]" in result

    def test_should_preserve_numbers(self) -> None:
        """Test that numbers are preserved."""
        assert sanitize_value(123) == 123
        assert sanitize_value(3.14) == 3.14

    def test_should_preserve_booleans(self) -> None:
        """Test that booleans are preserved."""
        assert sanitize_value(True) is True
        assert sanitize_value(False) is False

    def test_should_handle_none(self) -> None:
        """Test handling of None values."""
        assert sanitize_value(None) is None

    def test_should_sanitize_lists_recursively(self) -> None:
        """Test recursive sanitization of lists."""
        data = ["normal text", "user@example.com", 123, True]
        result = sanitize_value(data)

        assert result[0] == "normal text"
        assert "user@example.com" not in result[1]
        assert result[2] == 123
        assert result[3] is True

    def test_should_sanitize_dicts_recursively(self) -> None:
        """Test recursive sanitization of dictionaries."""
        data = {
            "name": "John",
            "email": "john@example.com",
            "age": 30,
            "active": True,
        }
        result = sanitize_value(data)

        assert result["name"] == "John"
        assert "john@example.com" not in result["email"]
        assert result["age"] == 30
        assert result["active"] is True

    def test_should_sanitize_nested_structures(self) -> None:
        """Test sanitization of deeply nested structures."""
        data = {
            "users": [
                {"name": "Alice", "email": "alice@example.com"},
                {"name": "Bob", "email": "bob@example.com"},
            ]
        }
        result = sanitize_value(data)

        assert "alice@example.com" not in str(result)
        assert "bob@example.com" not in str(result)

    def test_should_truncate_long_strings(self) -> None:
        """Test that very long strings are truncated."""
        long_string = "x" * 2000
        result = sanitize_value(long_string)

        assert len(result) == 1000  # Default max length

    def test_should_respect_custom_max_length(self) -> None:
        """Test using custom max string length."""
        config = PrivacyConfig(max_string_length=50)
        long_string = "x" * 100
        result = sanitize_value(long_string, config)

        assert len(result) == 50

    def test_should_sanitize_ip_with_non_hash_strategy(self) -> None:
        """Test IP sanitization with redact strategy."""
        config = PrivacyConfig(strategy="redact")
        result = sanitize_value("Server: 192.168.1.1", config)

        assert "192.168.1.1" not in result
        assert "X.X.X.X" in result

    def test_should_pass_through_unknown_types(self) -> None:
        """Test that unknown types are passed through unchanged."""

        class CustomType:
            pass

        obj = CustomType()
        result = sanitize_value(obj)

        assert result is obj


class TestRedactSensitiveKeys:
    """Test sensitive key redaction."""

    def test_should_redact_password_key(self) -> None:
        """Test that password key is redacted."""
        data = {"username": "john", "password": "secret123"}
        result = redact_sensitive_keys(data, ["password"])

        assert result["username"] == "john"
        assert result["password"] == "[REDACTED]"

    def test_should_redact_multiple_keys(self) -> None:
        """Test redacting multiple sensitive keys."""
        data = {
            "username": "john",
            "password": "secret123",
            "api_key": "abc123",
            "email": "john@example.com",
        }
        result = redact_sensitive_keys(data, ["password", "api_key"])

        assert result["username"] == "john"
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["email"] == "john@example.com"

    def test_should_handle_case_insensitive_matching(self) -> None:
        """Test that key matching is case-insensitive."""
        data = {"Password": "secret", "API_KEY": "abc123"}
        result = redact_sensitive_keys(data, ["password", "api_key"])

        assert result["Password"] == "[REDACTED]"
        assert result["API_KEY"] == "[REDACTED]"

    def test_should_handle_substring_matching(self) -> None:
        """Test that keys containing sensitive words are redacted."""
        data = {
            "user_password": "secret",
            "old_password": "old_secret",
            "my_api_key": "abc123",
        }
        result = redact_sensitive_keys(data, ["password", "api_key"])

        assert result["user_password"] == "[REDACTED]"
        assert result["old_password"] == "[REDACTED]"
        assert result["my_api_key"] == "[REDACTED]"

    def test_should_redact_nested_dicts(self) -> None:
        """Test redacting keys in nested dictionaries."""
        data = {
            "user": {
                "name": "john",
                "password": "secret",
                "settings": {"api_key": "abc123"},
            }
        }
        result = redact_sensitive_keys(data, ["password", "api_key"])

        assert result["user"]["name"] == "john"
        assert result["user"]["password"] == "[REDACTED]"
        assert result["user"]["settings"]["api_key"] == "[REDACTED]"

    def test_should_preserve_non_dict_values(self) -> None:
        """Test that non-dict values in nested structures are preserved."""
        data = {
            "items": [1, 2, 3],
            "password": "secret",
        }
        result = redact_sensitive_keys(data, ["password"])

        assert result["items"] == [1, 2, 3]
        assert result["password"] == "[REDACTED]"

    def test_should_use_custom_redaction_text(self) -> None:
        """Test using custom redaction text."""
        config = PrivacyConfig(redaction_text="[HIDDEN]")
        data = {"password": "secret"}
        result = redact_sensitive_keys(data, ["password"], config)

        assert result["password"] == "[HIDDEN]"


class TestSensitiveKeys:
    """Test SENSITIVE_KEYS constant."""

    def test_should_include_common_sensitive_keys(self) -> None:
        """Test that common sensitive keys are in the list."""
        assert "password" in SENSITIVE_KEYS
        assert "api_key" in SENSITIVE_KEYS
        assert "token" in SENSITIVE_KEYS
        assert "secret" in SENSITIVE_KEYS
        assert "credit_card" in SENSITIVE_KEYS

    def test_should_include_password_variants(self) -> None:
        """Test that password variants are included."""
        assert "passwd" in SENSITIVE_KEYS
        assert "pwd" in SENSITIVE_KEYS

    def test_should_include_token_variants(self) -> None:
        """Test that token variants are included."""
        assert "access_token" in SENSITIVE_KEYS
        assert "refresh_token" in SENSITIVE_KEYS


class TestSanitizeTelemetryData:
    """Test complete telemetry data sanitization."""

    def test_should_sanitize_all_pii_patterns(self) -> None:
        """Test that all PII patterns are sanitized."""
        data = {
            "email": "user@example.com",
            "phone": "+1-555-555-5555",
            "ip": "192.168.1.1",
            "path": "/home/user/project/file.py",
        }
        result = sanitize_telemetry_data(data)

        assert "user@example.com" not in str(result)
        assert "+1-555-555-5555" not in str(result)
        assert "192.168.1.1" not in str(result)
        assert "/home/user" not in str(result)

    def test_should_redact_sensitive_keys(self) -> None:
        """Test that sensitive keys are redacted."""
        data = {
            "username": "john",
            "password": "secret123",
            "api_key": "sk_live_abc123",
            "normal_field": "normal value",
        }
        result = sanitize_telemetry_data(data)

        assert result["username"] == "john"
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["normal_field"] == "normal value"

    def test_should_handle_complex_nested_data(self) -> None:
        """Test sanitizing complex nested telemetry data."""
        data = {
            "user": {
                "email": "user@example.com",
                "password": "secret",
                "preferences": {
                    "theme": "dark",
                },
            },
            "logs": [
                {"message": "User logged in from 192.168.1.1"},
                {"message": "API key used: sk_test_FAKE_KEY_NOT_REAL_12345678r"},
            ],
        }
        result = sanitize_telemetry_data(data)

        # Sensitive keys should be redacted
        assert result["user"]["password"] == "[REDACTED]"

        # PII in values should be sanitized
        assert "user@example.com" not in str(result)
        assert "192.168.1.1" not in str(result)
        assert "sk_test_FAKE_KEY_NOT_REAL_12345678r" not in str(result)

        # Normal data should be preserved
        assert result["user"]["preferences"]["theme"] == "dark"

    def test_should_preserve_safe_data(self) -> None:
        """Test that safe, non-PII data is preserved."""
        data = {
            "feature_name": "user_login",
            "count": 42,
            "success": True,
            "duration_ms": 123.45,
        }
        result = sanitize_telemetry_data(data)

        assert result == data

    def test_should_use_custom_config(self) -> None:
        """Test using custom privacy configuration."""
        config = PrivacyConfig(strategy="redact", redaction_text="[HIDDEN]")
        data = {
            "email": "user@example.com",
            "password": "secret",
        }
        result = sanitize_telemetry_data(data, config)

        assert result["email"] == "[HIDDEN]"
        assert result["password"] == "[HIDDEN]"


class TestPatterns:
    """Test PII detection patterns."""

    def test_phone_pattern_should_match_us_formats(self) -> None:
        """Test phone pattern matches US phone formats."""
        assert Patterns.PHONE.search("+1-555-555-5555") is not None
        assert Patterns.PHONE.search("(555) 555-5555") is not None
        assert Patterns.PHONE.search("555.555.5555") is not None
        assert Patterns.PHONE.search("555-555-5555") is not None

    def test_phone_pattern_should_match_international(self) -> None:
        """Test phone pattern matches international formats."""
        assert Patterns.PHONE.search("+44 20 7946 0958") is not None
        assert Patterns.PHONE.search("+44 1234 567890") is not None

    def test_email_pattern_should_match_valid_emails(self) -> None:
        """Test email pattern matches valid email addresses."""
        assert Patterns.EMAIL.search("user@example.com") is not None
        assert Patterns.EMAIL.search("test.user+tag@example.co.uk") is not None
        assert Patterns.EMAIL.search("user123@test-domain.com") is not None

    def test_api_key_pattern_should_match_common_formats(self) -> None:
        """Test API key pattern matches common formats."""
        assert Patterns.API_KEY.search("sk_test_FAKE_KEY_NOT_REAL_12345678r") is not None
        assert Patterns.API_KEY.search("Bearer abc123def456ghi789jkl012mno345pqr") is not None
        assert Patterns.API_KEY.search("api_key_abc123def456ghi789jkl012mno345pqr") is not None

    def test_credit_card_pattern_should_match_formats(self) -> None:
        """Test credit card pattern matches various formats."""
        assert Patterns.CREDIT_CARD.search("4532-1234-5678-9010") is not None
        assert Patterns.CREDIT_CARD.search("4532 1234 5678 9010") is not None
        assert Patterns.CREDIT_CARD.search("4532123456789010") is not None

    def test_ipv4_pattern_should_match_valid_ips(self) -> None:
        """Test IPv4 pattern matches valid IP addresses."""
        assert Patterns.IPV4.search("192.168.1.1") is not None
        assert Patterns.IPV4.search("10.0.0.255") is not None
        assert Patterns.IPV4.search("8.8.8.8") is not None

    def test_user_path_pattern_should_match_unix_paths(self) -> None:
        """Test user path pattern matches Unix paths."""
        assert Patterns.USER_PATH.search("/home/johndoe/project") is not None
        assert Patterns.USER_PATH.search("/Users/janedoe/Documents") is not None

    def test_user_path_pattern_should_match_windows_paths(self) -> None:
        """Test user path pattern matches Windows paths."""
        assert Patterns.USER_PATH.search("C:\\Users\\johndoe\\Documents") is not None
        assert Patterns.USER_PATH.search("D:\\Users\\janedoe\\Desktop") is not None


class TestPrivacyConfig:
    """Test PrivacyConfig dataclass."""

    def test_should_have_correct_defaults(self) -> None:
        """Test that PrivacyConfig has correct default values."""
        config = PrivacyConfig()

        assert config.strategy == "hash"
        assert config.max_string_length == 1000
        assert config.redaction_text == "[REDACTED]"

    def test_should_allow_custom_values(self) -> None:
        """Test creating PrivacyConfig with custom values."""
        config = PrivacyConfig(strategy="redact", max_string_length=500, redaction_text="[HIDDEN]")

        assert config.strategy == "redact"
        assert config.max_string_length == 500
        assert config.redaction_text == "[HIDDEN]"

    def test_default_config_constant(self) -> None:
        """Test DEFAULT_CONFIG constant."""
        assert DEFAULT_CONFIG.strategy == "hash"
        assert DEFAULT_CONFIG.max_string_length == 1000
        assert DEFAULT_CONFIG.redaction_text == "[REDACTED]"
