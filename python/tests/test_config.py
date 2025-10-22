"""
Comprehensive tests for configuration management.

Tests cover:
- Configuration creation and validation
- Environment variable loading
- Configuration merging (user config + env + defaults)
- Validation error messages
- Default values
- URL validation
- Timeout validation
"""

import pytest

from automagik_telemetry.config import (
    DEFAULT_CONFIG,
    ENV_VARS,
    TelemetryConfig,
    ValidatedConfig,
    _parse_boolean_env,
    create_config,
    load_config_from_env,
    merge_config,
    validate_config,
)


class TestBooleanParsing:
    """Test boolean environment variable parsing."""

    @pytest.mark.parametrize(
        "value", ["true", "TRUE", "True", "1", "yes", "YES", "Yes", "on", "ON", "On"]
    )
    def test_should_parse_truthy_values(self, value: str) -> None:
        """Test that various truthy values are parsed correctly."""
        assert _parse_boolean_env(value) is True

    @pytest.mark.parametrize(
        "value", ["false", "FALSE", "False", "0", "no", "NO", "No", "off", "OFF", "Off"]
    )
    def test_should_parse_falsy_values(self, value: str) -> None:
        """Test that various falsy values are parsed correctly."""
        assert _parse_boolean_env(value) is False

    def test_should_handle_whitespace(self) -> None:
        """Test that whitespace is trimmed before parsing."""
        assert _parse_boolean_env("  true  ") is True
        assert _parse_boolean_env("  false  ") is False


class TestLoadConfigFromEnv:
    """Test loading configuration from environment variables."""

    def test_should_load_enabled_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading enabled flag from environment."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        config = load_config_from_env()

        assert config.enabled is True

    def test_should_load_endpoint_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading endpoint from environment."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENDPOINT", "https://custom.example.com/traces")

        config = load_config_from_env()

        assert config.endpoint == "https://custom.example.com/traces"

    def test_should_load_verbose_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading verbose flag from environment."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_VERBOSE", "true")

        config = load_config_from_env()

        assert config.verbose is True

    def test_should_load_timeout_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading timeout from environment."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_TIMEOUT", "10000")

        config = load_config_from_env()

        assert config.timeout == 10000

    def test_should_ignore_invalid_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that invalid timeout values are ignored."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_TIMEOUT", "invalid")

        config = load_config_from_env()

        assert config.timeout is None

    def test_should_ignore_negative_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that negative timeout values are ignored."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_TIMEOUT", "-100")

        config = load_config_from_env()

        assert config.timeout is None

    def test_should_return_partial_config(self, clean_env: None) -> None:
        """Test that config from env has empty required fields."""
        config = load_config_from_env()

        assert config.project_name == ""
        assert config.version == ""
        assert config.endpoint is None
        assert config.enabled is None

    def test_should_load_all_env_vars_together(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading all environment variables at once."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENDPOINT", "https://custom.example.com/traces")
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_VERBOSE", "true")
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_TIMEOUT", "8000")

        config = load_config_from_env()

        assert config.enabled is True
        assert config.endpoint == "https://custom.example.com/traces"
        assert config.verbose is True
        assert config.timeout == 8000

    def test_should_ignore_zero_timeout_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that zero timeout from environment is ignored."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_TIMEOUT", "0")

        config = load_config_from_env()

        assert config.timeout is None

    def test_should_skip_empty_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that empty endpoint string is skipped."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENDPOINT", "")

        config = load_config_from_env()

        assert config.endpoint is None

    def test_should_skip_empty_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that empty timeout string is skipped."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_TIMEOUT", "")

        config = load_config_from_env()

        assert config.timeout is None


class TestValidateConfig:
    """Test configuration validation."""

    def test_should_accept_valid_config(self) -> None:
        """Test that valid configuration passes validation."""
        config = TelemetryConfig(project_name="test-project", version="1.0.0")

        # Should not raise
        validate_config(config)

    def test_should_reject_empty_project_name(self) -> None:
        """Test that empty project name raises error."""
        config = TelemetryConfig(project_name="", version="1.0.0")

        with pytest.raises(ValueError, match="project_name is required"):
            validate_config(config)

    def test_should_reject_whitespace_project_name(self) -> None:
        """Test that whitespace-only project name raises error."""
        config = TelemetryConfig(project_name="   ", version="1.0.0")

        with pytest.raises(ValueError, match="project_name is required"):
            validate_config(config)

    def test_should_reject_empty_version(self) -> None:
        """Test that empty version raises error."""
        config = TelemetryConfig(project_name="test-project", version="")

        with pytest.raises(ValueError, match="version is required"):
            validate_config(config)

    def test_should_reject_whitespace_version(self) -> None:
        """Test that whitespace-only version raises error."""
        config = TelemetryConfig(project_name="test-project", version="   ")

        with pytest.raises(ValueError, match="version is required"):
            validate_config(config)

    def test_should_reject_invalid_endpoint_url(self) -> None:
        """Test that invalid endpoint URL raises error."""
        config = TelemetryConfig(project_name="test-project", version="1.0.0", endpoint="not-a-url")

        with pytest.raises(ValueError, match="endpoint must use http or https"):
            validate_config(config)

    def test_should_reject_endpoint_without_scheme(self) -> None:
        """Test that endpoint without http/https raises error."""
        config = TelemetryConfig(
            project_name="test-project", version="1.0.0", endpoint="ftp://example.com/traces"
        )

        with pytest.raises(ValueError, match="endpoint must use http or https"):
            validate_config(config)

    def test_should_accept_http_endpoint(self) -> None:
        """Test that HTTP endpoint is accepted."""
        config = TelemetryConfig(
            project_name="test-project", version="1.0.0", endpoint="http://example.com/traces"
        )

        # Should not raise
        validate_config(config)

    def test_should_accept_https_endpoint(self) -> None:
        """Test that HTTPS endpoint is accepted."""
        config = TelemetryConfig(
            project_name="test-project", version="1.0.0", endpoint="https://example.com/traces"
        )

        # Should not raise
        validate_config(config)

    def test_should_reject_zero_timeout(self) -> None:
        """Test that zero timeout raises error."""
        config = TelemetryConfig(project_name="test-project", version="1.0.0", timeout=0)

        with pytest.raises(ValueError, match="timeout must be a positive integer"):
            validate_config(config)

    def test_should_reject_negative_timeout(self) -> None:
        """Test that negative timeout raises error."""
        config = TelemetryConfig(project_name="test-project", version="1.0.0", timeout=-100)

        with pytest.raises(ValueError, match="timeout must be a positive integer"):
            validate_config(config)

    def test_should_reject_excessive_timeout(self) -> None:
        """Test that timeout over 60 seconds raises error."""
        config = TelemetryConfig(project_name="test-project", version="1.0.0", timeout=70000)

        with pytest.raises(ValueError, match="timeout should not exceed 60000ms"):
            validate_config(config)

    def test_should_accept_valid_timeout(self) -> None:
        """Test that valid timeout is accepted."""
        config = TelemetryConfig(project_name="test-project", version="1.0.0", timeout=5000)

        # Should not raise
        validate_config(config)

    def test_should_reject_empty_organization(self) -> None:
        """Test that empty organization raises error."""
        config = TelemetryConfig(project_name="test-project", version="1.0.0", organization="   ")

        with pytest.raises(ValueError, match="organization cannot be empty"):
            validate_config(config)

    def test_should_reject_non_integer_timeout(self) -> None:
        """Test that non-integer timeout raises error."""
        config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            timeout="not-an-int",  # type: ignore
        )

        with pytest.raises(ValueError, match="timeout must be a positive integer"):
            validate_config(config)

    def test_should_accept_none_organization(self) -> None:
        """Test that None organization is accepted."""
        config = TelemetryConfig(project_name="test-project", version="1.0.0", organization=None)

        # Should not raise
        validate_config(config)

    def test_should_reject_endpoint_without_netloc(self) -> None:
        """Test that endpoint without network location raises error."""
        config = TelemetryConfig(project_name="test-project", version="1.0.0", endpoint="http://")

        with pytest.raises(ValueError, match="endpoint must be a valid URL"):
            validate_config(config)

    def test_should_handle_general_url_parse_error(self) -> None:
        """Test handling of general URL parsing errors."""
        config = TelemetryConfig(
            project_name="test-project", version="1.0.0", endpoint="ht!tp://invalid"
        )

        with pytest.raises(ValueError, match="endpoint must use http or https"):
            validate_config(config)

    def test_should_handle_unexpected_url_parse_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test handling of unexpected exceptions during URL parsing."""
        from unittest.mock import Mock

        config = TelemetryConfig(
            project_name="test-project", version="1.0.0", endpoint="http://example.com"
        )

        # Patch urlparse to raise a non-ValueError exception
        def mock_urlparse(url: str) -> Mock:
            raise RuntimeError("Unexpected error")

        monkeypatch.setattr("automagik_telemetry.config.urlparse", mock_urlparse)

        with pytest.raises(ValueError, match="endpoint must be a valid URL"):
            validate_config(config)


class TestMergeConfig:
    """Test configuration merging."""

    def test_should_use_user_config_values(self) -> None:
        """Test that user-provided values take precedence."""
        user_config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            endpoint="https://custom.example.com/traces",
            organization="custom-org",
            timeout=8000,
            enabled=True,
            verbose=True,
        )

        result = merge_config(user_config)

        assert result.project_name == "test-project"
        assert result.version == "1.0.0"
        assert result.endpoint == "https://custom.example.com/traces"
        assert result.organization == "custom-org"
        assert result.timeout == 8000
        assert result.enabled is True
        assert result.verbose is True

    def test_should_use_defaults_for_missing_values(self, clean_env: None) -> None:
        """Test that defaults are used for missing optional values."""
        user_config = TelemetryConfig(project_name="test-project", version="1.0.0")

        result = merge_config(user_config)

        assert result.endpoint == DEFAULT_CONFIG["endpoint"]
        assert result.organization == DEFAULT_CONFIG["organization"]
        assert result.timeout == DEFAULT_CONFIG["timeout"]
        assert result.enabled == DEFAULT_CONFIG["enabled"]
        assert result.verbose == DEFAULT_CONFIG["verbose"]

    def test_should_prefer_user_config_over_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that user config takes precedence over environment variables."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENDPOINT", "https://env.example.com/traces")
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "false")

        user_config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            endpoint="https://user.example.com/traces",
            enabled=True,
        )

        result = merge_config(user_config)

        assert result.endpoint == "https://user.example.com/traces"
        assert result.enabled is True

    def test_should_prefer_env_over_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that env vars take precedence over defaults."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENDPOINT", "https://env.example.com/traces")
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_TIMEOUT", "7000")

        user_config = TelemetryConfig(project_name="test-project", version="1.0.0")

        result = merge_config(user_config)

        assert result.endpoint == "https://env.example.com/traces"
        assert result.enabled is True
        assert result.timeout == 7000

    def test_should_handle_boolean_merge_correctly(self, clean_env: None) -> None:
        """Test that boolean merging handles None vs False correctly."""
        # enabled=False in user config should override default
        user_config = TelemetryConfig(project_name="test-project", version="1.0.0", enabled=False)

        result = merge_config(user_config)

        assert result.enabled is False

    def test_should_return_validated_config_type(self, clean_env: None) -> None:
        """Test that merge_config returns ValidatedConfig instance."""
        user_config = TelemetryConfig(project_name="test-project", version="1.0.0")

        result = merge_config(user_config)

        assert isinstance(result, ValidatedConfig)
        # All fields should be non-optional
        assert result.endpoint is not None
        assert result.organization is not None
        assert result.timeout is not None
        assert result.enabled is not None
        assert result.verbose is not None

    def test_should_merge_env_enabled_over_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that env enabled takes precedence over default when user doesn't specify."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        user_config = TelemetryConfig(project_name="test-project", version="1.0.0")

        result = merge_config(user_config)

        assert result.enabled is True

    def test_should_merge_env_verbose_over_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that env verbose takes precedence over default when user doesn't specify."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_VERBOSE", "true")

        user_config = TelemetryConfig(project_name="test-project", version="1.0.0")

        result = merge_config(user_config)

        assert result.verbose is True

    def test_should_handle_user_verbose_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that explicit False for verbose is respected."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_VERBOSE", "true")

        user_config = TelemetryConfig(project_name="test-project", version="1.0.0", verbose=False)

        result = merge_config(user_config)

        # User's explicit False should win
        assert result.verbose is False


class TestCreateConfig:
    """Test complete configuration creation."""

    def test_should_create_valid_config(self) -> None:
        """Test creating a complete valid configuration."""
        user_config = TelemetryConfig(project_name="test-project", version="1.0.0")

        result = create_config(user_config)

        assert isinstance(result, ValidatedConfig)
        assert result.project_name == "test-project"
        assert result.version == "1.0.0"

    def test_should_validate_before_merging(self) -> None:
        """Test that validation happens before merging."""
        invalid_config = TelemetryConfig(project_name="", version="1.0.0")

        with pytest.raises(ValueError, match="project_name is required"):
            create_config(invalid_config)

    def test_should_reject_invalid_endpoint_in_create(self) -> None:
        """Test that invalid endpoint is caught in create_config."""
        config = TelemetryConfig(
            project_name="test-project", version="1.0.0", endpoint="invalid-url"
        )

        with pytest.raises(ValueError, match="endpoint must use http or https"):
            create_config(config)

    def test_should_accept_valid_config_with_all_fields(self) -> None:
        """Test creating config with all fields specified."""
        user_config = TelemetryConfig(
            project_name="omni",
            version="2.0.0",
            endpoint="https://telemetry.custom.com/v1/traces",
            organization="custom-org",
            timeout=10000,
            enabled=True,
            verbose=False,
        )

        result = create_config(user_config)

        assert result.project_name == "omni"
        assert result.version == "2.0.0"
        assert result.endpoint == "https://telemetry.custom.com/v1/traces"
        assert result.organization == "custom-org"
        assert result.timeout == 10000
        assert result.enabled is True
        assert result.verbose is False


class TestDefaultConfig:
    """Test default configuration values."""

    def test_should_have_correct_default_endpoint(self) -> None:
        """Test that default endpoint is correct."""
        assert DEFAULT_CONFIG["endpoint"] == "https://telemetry.namastex.ai/v1/traces"

    def test_should_have_correct_default_organization(self) -> None:
        """Test that default organization is namastex."""
        assert DEFAULT_CONFIG["organization"] == "namastex"

    def test_should_have_correct_default_timeout(self) -> None:
        """Test that default timeout is 5000ms."""
        assert DEFAULT_CONFIG["timeout"] == 5000

    def test_should_be_disabled_by_default(self) -> None:
        """Test that telemetry is disabled by default (opt-in only)."""
        assert DEFAULT_CONFIG["enabled"] is False

    def test_should_not_be_verbose_by_default(self) -> None:
        """Test that verbose mode is off by default."""
        assert DEFAULT_CONFIG["verbose"] is False


class TestEnvVars:
    """Test environment variable constants."""

    def test_should_have_correct_env_var_names(self) -> None:
        """Test that environment variable names are correct."""
        assert ENV_VARS["ENABLED"] == "AUTOMAGIK_TELEMETRY_ENABLED"
        assert ENV_VARS["ENDPOINT"] == "AUTOMAGIK_TELEMETRY_ENDPOINT"
        assert ENV_VARS["VERBOSE"] == "AUTOMAGIK_TELEMETRY_VERBOSE"
        assert ENV_VARS["TIMEOUT"] == "AUTOMAGIK_TELEMETRY_TIMEOUT"


class TestConfigPriority:
    """Test configuration priority (user > env > defaults)."""

    def test_priority_all_three_sources(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test priority when all three sources provide values."""
        # Set environment variables
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENDPOINT", "https://env.example.com/traces")
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_TIMEOUT", "6000")

        # User config
        user_config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            endpoint="https://user.example.com/traces",
            # timeout not specified - should come from env
            # organization not specified - should come from defaults
        )

        result = merge_config(user_config)

        # User config wins for endpoint
        assert result.endpoint == "https://user.example.com/traces"
        # Env wins for timeout
        assert result.timeout == 6000
        # Default wins for organization
        assert result.organization == DEFAULT_CONFIG["organization"]

    def test_priority_with_explicit_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that explicit False in user config overrides True in env."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        user_config = TelemetryConfig(
            project_name="test-project",
            version="1.0.0",
            enabled=False,  # Explicit False
        )

        result = merge_config(user_config)

        # User's explicit False should win
        assert result.enabled is False
