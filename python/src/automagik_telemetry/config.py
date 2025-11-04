"""
Configuration management for Automagik Telemetry SDK.

Provides centralized configuration with environment variable support,
sensible defaults, and validation.
"""

import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class TelemetryConfig:
    """
    Configuration for telemetry client.

    Attributes:
        project_name: Name of the Automagik project
        version: Version of the project
        backend: Backend to use ("otlp" or "clickhouse", default: "otlp")
        endpoint: Custom telemetry endpoint (defaults to telemetry.namastex.ai)
        organization: Organization name (default: namastex)
        timeout: HTTP timeout in seconds (None = use env var or default: 5)
        batch_size: Number of events to batch before sending (default: 100 for optimal performance)
        flush_interval: Seconds between automatic flushes (default: 5.0)
        compression_enabled: Enable gzip compression (default: True)
        compression_threshold: Minimum payload size for compression in bytes (default: 1024)
        max_retries: Maximum number of retry attempts (default: 3)
        retry_backoff_base: Base backoff time in seconds (default: 1.0)
        metrics_endpoint: Custom endpoint for metrics (defaults to /v1/metrics)
        logs_endpoint: Custom endpoint for logs (defaults to /v1/logs)
        enabled: Enable/disable telemetry (None = auto-detect from environment)
        verbose: Enable verbose logging (None = use AUTOMAGIK_TELEMETRY_VERBOSE env var)
        clickhouse_endpoint: ClickHouse HTTP endpoint (default: http://localhost:8123)
        clickhouse_database: ClickHouse database name (default: telemetry)
        clickhouse_table: ClickHouse table name for traces (default: traces)
        clickhouse_metrics_table: ClickHouse table name for metrics (default: metrics)
        clickhouse_logs_table: ClickHouse table name for logs (default: logs)
        clickhouse_username: ClickHouse username (default: default)
        clickhouse_password: ClickHouse password (default: "")
    """

    project_name: str
    version: str
    backend: str = "otlp"  # "otlp" or "clickhouse"
    endpoint: str | None = None
    organization: str = "namastex"
    timeout: int | None = None  # None = use env var or default
    batch_size: int = 100  # Batch events for optimal performance
    flush_interval: float = 5.0
    compression_enabled: bool = True
    compression_threshold: int = 1024
    max_retries: int = 3
    retry_backoff_base: float = 1.0
    metrics_endpoint: str | None = None
    logs_endpoint: str | None = None
    enabled: bool | None = None  # Enable/disable telemetry (None = auto-detect from environment)
    verbose: bool | None = None  # Enable verbose logging (None = use environment variable)
    # ClickHouse-specific options
    clickhouse_endpoint: str = "http://localhost:8123"
    clickhouse_database: str = "telemetry"
    clickhouse_table: str = "traces"
    clickhouse_metrics_table: str = "metrics"
    clickhouse_logs_table: str = "logs"
    clickhouse_username: str = "default"
    clickhouse_password: str = ""


@dataclass
class ConfigSchema:
    """
    Basic telemetry configuration schema for environment variable loading.

    This is the minimal configuration structure used internally for loading
    configuration from environment variables. For the full client configuration,
    use TelemetryConfig from the main client module.

    Attributes:
        project_name: Name of the Automagik project (omni, hive, forge, etc.)
        version: Version of the project
        endpoint: Custom telemetry endpoint (defaults to telemetry.namastex.ai)
        organization: Organization name
        timeout: HTTP timeout in seconds (default: 5)
        enabled: Whether telemetry is enabled (opt-in only)
        verbose: Enable verbose logging to console

    Example:
        >>> config = ConfigSchema(
        ...     project_name="omni",
        ...     version="1.0.0",
        ...     endpoint="https://telemetry.namastex.ai/v1/traces",
        ...     organization="namastex",
        ...     timeout=5,
        ...     enabled=True,
        ...     verbose=False
        ... )
    """

    project_name: str
    version: str
    endpoint: str | None = None
    organization: str | None = None
    timeout: int | None = None  # seconds
    enabled: bool | None = None
    verbose: bool | None = None


@dataclass
class ValidatedConfig:
    """
    Internal validated configuration with all defaults applied.

    All optional fields from TelemetryConfig are resolved to concrete values.
    """

    project_name: str
    version: str
    endpoint: str
    organization: str
    timeout: int  # seconds
    enabled: bool
    verbose: bool


# Default configuration values
DEFAULT_CONFIG: dict[str, str | int | bool] = {
    "endpoint": "https://telemetry.namastex.ai/v1/traces",
    "organization": "namastex",
    "timeout": 5,  # seconds
    "enabled": False,  # Disabled by default - opt-in only
    "verbose": False,
}

# Environment variables used for configuration
ENV_VARS = {
    "ENABLED": "AUTOMAGIK_TELEMETRY_ENABLED",
    "ENDPOINT": "AUTOMAGIK_TELEMETRY_ENDPOINT",
    "VERBOSE": "AUTOMAGIK_TELEMETRY_VERBOSE",
    "TIMEOUT": "AUTOMAGIK_TELEMETRY_TIMEOUT",
}


def _parse_boolean_env(value: str) -> bool:
    """
    Parse boolean value from environment variable string.

    Args:
        value: Environment variable value

    Returns:
        Boolean value

    Example:
        >>> _parse_boolean_env("true")
        True
        >>> _parse_boolean_env("0")
        False
        >>> _parse_boolean_env("yes")
        True
    """
    normalized = value.lower().strip()
    return normalized in ("true", "1", "yes", "on")


def load_config_from_env() -> ConfigSchema:
    """
    Load configuration from environment variables.

    Supported environment variables:
    - AUTOMAGIK_TELEMETRY_ENABLED: Enable/disable telemetry (true/false/1/0/yes/no/on/off)
    - AUTOMAGIK_TELEMETRY_ENDPOINT: Custom telemetry endpoint URL
    - AUTOMAGIK_TELEMETRY_VERBOSE: Enable verbose logging (true/false/1/0/yes/no/on/off)
    - AUTOMAGIK_TELEMETRY_TIMEOUT: HTTP timeout in seconds

    Returns:
        Partial configuration from environment variables

    Example:
        >>> # Set environment variables
        >>> os.environ["AUTOMAGIK_TELEMETRY_ENABLED"] = "true"
        >>> os.environ["AUTOMAGIK_TELEMETRY_TIMEOUT"] = "10"
        >>>
        >>> config = load_config_from_env()
        >>> config.enabled
        True
        >>> config.timeout
        10
    """
    config = ConfigSchema(
        project_name="",  # Not set from env
        version="",  # Not set from env
    )

    # Parse enabled flag
    enabled_env = os.getenv(ENV_VARS["ENABLED"])
    if enabled_env is not None:
        config.enabled = _parse_boolean_env(enabled_env)

    # Parse endpoint
    endpoint_env = os.getenv(ENV_VARS["ENDPOINT"])
    if endpoint_env:
        config.endpoint = endpoint_env

    # Parse verbose flag
    verbose_env = os.getenv(ENV_VARS["VERBOSE"])
    if verbose_env is not None:
        config.verbose = _parse_boolean_env(verbose_env)

    # Parse timeout
    timeout_env = os.getenv(ENV_VARS["TIMEOUT"])
    if timeout_env:
        try:
            timeout = int(timeout_env)
            if timeout > 0:
                config.timeout = timeout
        except ValueError:
            pass  # Invalid timeout, skip it

    return config


def merge_config(user_config: TelemetryConfig) -> ValidatedConfig:
    """
    Merge user configuration with defaults and environment variables.

    Priority (highest to lowest):
    1. User-provided config (if explicitly set, i.e., not None)
    2. Environment variables (if set)
    3. Default values

    Args:
        user_config: User-provided configuration

    Returns:
        Validated configuration with all defaults applied

    Example:
        >>> user_config = TelemetryConfig(
        ...     project_name="omni",
        ...     version="1.0.0",
        ...     enabled=True
        ... )
        >>> validated = merge_config(user_config)
        >>> validated.endpoint
        'https://telemetry.namastex.ai/v1/traces'
        >>> validated.enabled
        True
    """
    env_config = load_config_from_env()

    return ValidatedConfig(
        project_name=user_config.project_name,
        version=user_config.version,
        endpoint=str(user_config.endpoint or env_config.endpoint or DEFAULT_CONFIG["endpoint"]),
        organization=str(user_config.organization or DEFAULT_CONFIG["organization"]),
        timeout=int(
            user_config.timeout
            if user_config.timeout is not None
            else (env_config.timeout if env_config.timeout is not None else DEFAULT_CONFIG["timeout"])
        ),
        enabled=bool(
            user_config.enabled
            if user_config.enabled is not None
            else (
                env_config.enabled if env_config.enabled is not None else DEFAULT_CONFIG["enabled"]
            )
        ),
        verbose=bool(
            user_config.verbose
            if user_config.verbose is not None
            else (
                env_config.verbose if env_config.verbose is not None else DEFAULT_CONFIG["verbose"]
            )
        ),
    )


def validate_config(config: TelemetryConfig) -> None:
    """
    Validate configuration values and throw helpful errors.

    Args:
        config: Configuration to validate

    Raises:
        ValueError: If configuration is invalid

    Example:
        >>> config = TelemetryConfig(project_name="", version="1.0.0")
        >>> validate_config(config)
        Traceback (most recent call last):
            ...
        ValueError: TelemetryConfig: project_name is required and cannot be empty
    """
    # Validate required fields
    if not config.project_name or not config.project_name.strip():
        raise ValueError("TelemetryConfig: project_name is required and cannot be empty")

    if not config.version or not config.version.strip():
        raise ValueError("TelemetryConfig: version is required and cannot be empty")

    # Validate endpoint URL format if provided
    if config.endpoint is not None:
        try:
            parsed = urlparse(config.endpoint)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("TelemetryConfig: endpoint must use http or https protocol")
            if not parsed.netloc:
                raise ValueError(
                    f"TelemetryConfig: endpoint must be a valid URL (got: {config.endpoint})"
                )
        except Exception as e:
            if "endpoint must" in str(e):
                raise
            raise ValueError(
                f"TelemetryConfig: endpoint must be a valid URL (got: {config.endpoint})"
            )

    # Validate timeout if provided
    if config.timeout is not None:
        if not isinstance(config.timeout, int) or config.timeout <= 0:
            raise ValueError(
                f"TelemetryConfig: timeout must be a positive integer (got: {config.timeout})"
            )
        if config.timeout > 60:
            raise ValueError(
                f"TelemetryConfig: timeout should not exceed 60 seconds (got: {config.timeout})"
            )

    # Validate organization if provided
    if config.organization is not None and not config.organization.strip():
        raise ValueError("TelemetryConfig: organization cannot be empty if provided")


def create_config(user_config: TelemetryConfig) -> ValidatedConfig:
    """
    Create and validate a complete configuration.

    This is the main entry point for configuration creation.

    Args:
        user_config: User-provided configuration

    Returns:
        Validated configuration ready for use

    Raises:
        ValueError: If configuration is invalid

    Example:
        >>> config = create_config(TelemetryConfig(
        ...     project_name="omni",
        ...     version="1.0.0",
        ...     enabled=True
        ... ))
        >>> config.project_name
        'omni'
        >>> config.endpoint
        'https://telemetry.namastex.ai/v1/traces'
        >>> config.enabled
        True
    """
    validate_config(user_config)
    return merge_config(user_config)
