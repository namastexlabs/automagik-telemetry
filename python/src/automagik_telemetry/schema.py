"""Standard event schema for cross-repo telemetry"""


class StandardEvents:
    """
    Standardized event types used across all Automagik projects.
    Ensures consistent telemetry data collection.
    """

    # Feature usage tracking
    FEATURE_USED = "automagik.feature.used"
    # Attributes: {project, feature_name, feature_category}

    # API request tracking
    API_REQUEST = "automagik.api.request"
    # Attributes: {project, endpoint, method, status}

    # CLI command execution
    COMMAND_EXECUTED = "automagik.cli.command"
    # Attributes: {project, command, subcommand}

    # Performance metrics
    OPERATION_LATENCY = "automagik.performance.latency"
    # Attributes: {project, operation_type, duration_ms}

    # Error tracking
    ERROR_OCCURRED = "automagik.error"
    # Attributes: {project, error_code, error_category, severity}

    # Service health
    SERVICE_HEALTH = "automagik.health"
    # Attributes: {project, service_name, status}
