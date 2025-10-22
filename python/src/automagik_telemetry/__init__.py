"""
Automagik Telemetry SDK

Privacy-first, opt-in telemetry for the Automagik ecosystem.
"""

from automagik_telemetry.client import (
    TelemetryClient,
    TelemetryConfig as ClientTelemetryConfig,
    MetricType,
    LogSeverity,
)
from automagik_telemetry.config import (
    TelemetryConfig,
    ValidatedConfig,
    create_config,
    load_config_from_env,
    merge_config,
    validate_config,
    DEFAULT_CONFIG,
    ENV_VARS,
)
from automagik_telemetry.opt_in import (
    TelemetryOptIn,
    prompt_user_if_needed,
    should_prompt_user,
)
from automagik_telemetry.privacy import (
    PrivacyConfig,
    SENSITIVE_KEYS,
    detect_pii,
    hash_value,
    redact_sensitive_keys,
    sanitize_email,
    sanitize_phone,
    sanitize_telemetry_data,
    sanitize_value,
    truncate_string,
)
from automagik_telemetry.schema import StandardEvents

__version__ = "0.2.0"
__all__ = [
    # Core client
    "TelemetryClient",
    "ClientTelemetryConfig",
    "MetricType",
    "LogSeverity",
    "StandardEvents",
    # Opt-in utilities
    "TelemetryOptIn",
    "prompt_user_if_needed",
    "should_prompt_user",
    # Configuration
    "TelemetryConfig",
    "ValidatedConfig",
    "create_config",
    "load_config_from_env",
    "merge_config",
    "validate_config",
    "DEFAULT_CONFIG",
    "ENV_VARS",
    # Privacy utilities
    "PrivacyConfig",
    "SENSITIVE_KEYS",
    "detect_pii",
    "hash_value",
    "redact_sensitive_keys",
    "sanitize_email",
    "sanitize_phone",
    "sanitize_telemetry_data",
    "sanitize_value",
    "truncate_string",
]

# Note: Async methods are instance methods of TelemetryClient, not module-level exports:
# - TelemetryClient.track_event_async()
# - TelemetryClient.track_error_async()
# - TelemetryClient.track_metric_async()
# - TelemetryClient.track_log_async()
# - TelemetryClient.flush_async()
