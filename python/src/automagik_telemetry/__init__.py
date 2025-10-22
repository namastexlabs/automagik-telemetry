"""
Automagik Telemetry SDK

Privacy-first, opt-in telemetry for the Automagik ecosystem.

Note: TelemetryClient is deprecated. Use AutomagikTelemetry instead.
TelemetryClient is maintained as an alias for backwards compatibility.
"""

from automagik_telemetry.client import (
    AutomagikTelemetry,
    LogSeverity,
    MetricType,
    TelemetryClient,  # Backwards compatibility alias
)
from automagik_telemetry.client import (
    TelemetryConfig as ClientTelemetryConfig,
)
from automagik_telemetry.config import (
    DEFAULT_CONFIG,
    ENV_VARS,
    TelemetryConfig,
    ValidatedConfig,
    create_config,
    load_config_from_env,
    merge_config,
    validate_config,
)
from automagik_telemetry.opt_in import (
    TelemetryOptIn,
    prompt_user_if_needed,
    should_prompt_user,
)
from automagik_telemetry.privacy import (
    SENSITIVE_KEYS,
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
from automagik_telemetry.schema import StandardEvents

__version__ = "0.2.0"
__all__ = [
    # Core client (primary name)
    "AutomagikTelemetry",
    # Backwards compatibility alias (deprecated)
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

# Note: Async methods are instance methods of AutomagikTelemetry, not module-level exports:
# - AutomagikTelemetry.track_event_async()
# - AutomagikTelemetry.track_error_async()
# - AutomagikTelemetry.track_metric_async()
# - AutomagikTelemetry.track_log_async()
# - AutomagikTelemetry.flush_async()
