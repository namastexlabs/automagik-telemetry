"""
Production-ready telemetry client implementation.

Based on battle-tested code from automagik-omni and automagik-spark.
Uses only Python standard library - no external dependencies.
"""

import asyncio
import gzip
import json
import logging
import os
import platform
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """OTLP metric types."""

    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"


class LogSeverity(Enum):
    """OTLP log severity levels."""

    TRACE = 1
    DEBUG = 5
    INFO = 9
    WARN = 13
    ERROR = 17
    FATAL = 21


@dataclass
class TelemetryConfig:
    """
    Configuration for telemetry client.

    Attributes:
        project_name: Name of the Automagik project
        version: Version of the project
        endpoint: Custom telemetry endpoint (defaults to telemetry.namastex.ai)
        organization: Organization name (default: namastex)
        timeout: HTTP timeout in seconds (default: 5)
        batch_size: Number of events to batch before sending (default: 1 for immediate send)
        flush_interval: Seconds between automatic flushes (default: 5.0)
        compression_enabled: Enable gzip compression (default: True)
        compression_threshold: Minimum payload size for compression in bytes (default: 1024)
        max_retries: Maximum number of retry attempts (default: 3)
        retry_backoff_base: Base backoff time in seconds (default: 1.0)
        metrics_endpoint: Custom endpoint for metrics (defaults to /v1/metrics)
        logs_endpoint: Custom endpoint for logs (defaults to /v1/logs)
    """

    project_name: str
    version: str
    endpoint: str | None = None
    organization: str = "namastex"
    timeout: int = 5
    batch_size: int = 1  # Default to immediate send for backward compatibility
    flush_interval: float = 5.0
    compression_enabled: bool = True
    compression_threshold: int = 1024
    max_retries: int = 3
    retry_backoff_base: float = 1.0
    metrics_endpoint: str | None = None
    logs_endpoint: str | None = None


class AutomagikTelemetry:
    """
    Privacy-first telemetry client for Automagik projects.

    Features:
    - Disabled by default - users must explicitly opt-in
    - Uses only stdlib - no external dependencies
    - Sends OTLP-compatible traces, metrics, and logs
    - Batch processing with configurable flush intervals
    - Automatic gzip compression for large payloads
    - Retry logic with exponential backoff
    - Silent failures - never crashes your app
    - Auto-disables in CI/test environments

    Example:
        >>> from automagik_telemetry import AutomagikTelemetry, StandardEvents
        >>>
        >>> # Simple initialization (backward compatible)
        >>> telemetry = AutomagikTelemetry(
        ...     project_name="omni",
        ...     version="1.0.0"
        ... )
        >>>
        >>> # Advanced initialization with custom config
        >>> from automagik_telemetry import TelemetryConfig
        >>> config = TelemetryConfig(
        ...     project_name="omni",
        ...     version="1.0.0",
        ...     batch_size=50,
        ...     compression_enabled=True
        ... )
        >>> telemetry = AutomagikTelemetry(config=config)
        >>>
        >>> telemetry.track_event(StandardEvents.FEATURE_USED, {
        ...     "feature_name": "list_contacts"
        ... })
    """

    def __init__(
        self,
        project_name: str | None = None,
        version: str | None = None,
        endpoint: str | None = None,
        organization: str = "namastex",
        timeout: int = 5,
        config: TelemetryConfig | None = None,
    ):
        """
        Initialize telemetry client.

        Args:
            project_name: Name of the Automagik project (omni, hive, forge, etc.)
            version: Version of the project
            endpoint: Custom telemetry endpoint (defaults to telemetry.namastex.ai)
            organization: Organization name (default: namastex)
            timeout: HTTP timeout in seconds (default: 5)
            config: TelemetryConfig instance for advanced configuration (overrides individual params)
        """
        # Support both old and new initialization styles
        if config is not None:
            self.config = config
        else:
            if project_name is None or version is None:
                raise ValueError(
                    "Either 'config' or both 'project_name' and 'version' must be provided"
                )
            self.config = TelemetryConfig(
                project_name=project_name,
                version=version,
                endpoint=endpoint,
                organization=organization,
                timeout=timeout,
            )

        # Convenience properties for backward compatibility
        self.project_name = self.config.project_name
        self.project_version = self.config.version
        self.organization = self.config.organization
        self.timeout = self.config.timeout

        # Set up endpoints
        base_endpoint = self.config.endpoint or os.getenv(
            "AUTOMAGIK_TELEMETRY_ENDPOINT",
            "https://telemetry.namastex.ai/v1/traces",  # Legacy default includes /v1/traces
        )

        # Ensure base endpoint doesn't have trailing slash
        if base_endpoint:
            base_endpoint = base_endpoint.rstrip("/")

        # Set specific endpoints
        # Check if endpoint already has a path component (ends with /traces, /v1/traces, etc.)
        # This handles backward compatibility where users might pass full endpoints
        if base_endpoint and (
            base_endpoint.endswith("/traces")
            or base_endpoint.endswith("/metrics")
            or base_endpoint.endswith("/logs")
        ):
            # Endpoint already includes path - use as-is
            self.endpoint = base_endpoint
            # Extract base for other endpoints
            if "/v1/" in base_endpoint:
                base_for_others = base_endpoint.rsplit("/v1/", 1)[0]
                self.metrics_endpoint = (
                    self.config.metrics_endpoint or f"{base_for_others}/v1/metrics"
                )
                self.logs_endpoint = self.config.logs_endpoint or f"{base_for_others}/v1/logs"
            else:
                # Custom endpoint without /v1/ - just replace the last path component
                base_for_others = base_endpoint.rsplit("/", 1)[0]
                self.metrics_endpoint = self.config.metrics_endpoint or f"{base_for_others}/metrics"
                self.logs_endpoint = self.config.logs_endpoint or f"{base_for_others}/logs"
        else:
            # New format - just base URL
            base_url = base_endpoint or "https://telemetry.namastex.ai"
            self.endpoint = f"{base_url}/v1/traces"
            self.metrics_endpoint = self.config.metrics_endpoint or f"{base_url}/v1/metrics"
            self.logs_endpoint = self.config.logs_endpoint or f"{base_url}/v1/logs"

        # User & session IDs
        self.user_id = self._get_or_create_user_id()
        self.session_id = str(uuid.uuid4())

        # Enable/disable check
        self.enabled = self._is_telemetry_enabled()

        # Verbose mode (print events to console)
        self.verbose = os.getenv("AUTOMAGIK_TELEMETRY_VERBOSE", "false").lower() == "true"

        # Batch processing queues
        self._trace_queue: deque = deque()
        self._metric_queue: deque = deque()
        self._log_queue: deque = deque()
        self._queue_lock = threading.Lock()

        # Background flush timer
        self._flush_timer: threading.Timer | None = None
        self._shutdown = False

        # Start flush timer if batching is enabled
        if self.config.batch_size > 1:
            self._schedule_flush()

    def _get_or_create_user_id(self) -> str:
        """Generate or retrieve anonymous user identifier."""
        user_id_file = Path.home() / ".automagik" / "user_id"

        if user_id_file.exists():
            try:
                return user_id_file.read_text().strip()
            except Exception:
                pass

        # Create new anonymous UUID
        user_id = str(uuid.uuid4())
        try:
            user_id_file.parent.mkdir(parents=True, exist_ok=True)
            user_id_file.write_text(user_id)
        except Exception:
            pass  # Continue with in-memory ID if file creation fails

        return user_id

    def _is_telemetry_enabled(self) -> bool:
        """Check if telemetry is enabled based on various opt-out mechanisms."""
        # Explicit enable/disable via environment variable
        env_var = os.getenv("AUTOMAGIK_TELEMETRY_ENABLED")
        if env_var is not None:
            return env_var.lower() in ("true", "1", "yes", "on")

        # Check for opt-out file
        if (Path.home() / ".automagik-no-telemetry").exists():
            return False

        # Auto-disable in CI/testing environments
        ci_environments = [
            "CI",
            "GITHUB_ACTIONS",
            "TRAVIS",
            "JENKINS",
            "GITLAB_CI",
            "CIRCLECI",
        ]
        if any(os.getenv(var) for var in ci_environments):
            return False

        # Check for development indicators
        if os.getenv("ENVIRONMENT") in ["development", "dev", "test", "testing"]:
            return False

        # Default: disabled (opt-in only)
        return False

    def _get_system_info(self) -> dict[str, Any]:
        """Collect basic system information (no PII)."""
        return {
            "os": platform.system(),
            "os_version": platform.release(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "architecture": platform.machine(),
            "is_docker": os.path.exists("/.dockerenv"),
            "project_name": self.project_name,
            "project_version": self.project_version,
            "organization": self.organization,
        }

    def _create_attributes(
        self, data: dict[str, Any], include_system: bool = True
    ) -> list[dict[str, Any]]:
        """Convert data to OTLP attribute format with type safety."""
        attributes = []

        # Add system information
        if include_system:
            system_info = self._get_system_info()
            for key, value in system_info.items():
                if isinstance(value, bool):
                    attributes.append({"key": f"system.{key}", "value": {"boolValue": value}})
                elif isinstance(value, (int, float)):
                    attributes.append(
                        {"key": f"system.{key}", "value": {"doubleValue": float(value)}}
                    )
                else:
                    attributes.append(
                        {"key": f"system.{key}", "value": {"stringValue": str(value)}}
                    )

        # Add event data
        for key, value in data.items():
            if isinstance(value, bool):
                attributes.append({"key": key, "value": {"boolValue": value}})
            elif isinstance(value, (int, float)):
                attributes.append({"key": key, "value": {"doubleValue": float(value)}})
            else:
                # Truncate long strings to prevent payload bloat
                sanitized_value = str(value)[:500]
                attributes.append({"key": key, "value": {"stringValue": sanitized_value}})

        return attributes

    def _schedule_flush(self) -> None:
        """Schedule automatic flush after flush_interval."""
        if self._shutdown:
            return

        def flush_and_reschedule() -> None:
            if not self._shutdown:
                self.flush()
                self._schedule_flush()

        self._flush_timer = threading.Timer(self.config.flush_interval, flush_and_reschedule)
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def _compress_payload(self, payload: bytes) -> bytes:
        """Compress payload using gzip if it exceeds threshold."""
        if self.config.compression_enabled and len(payload) >= self.config.compression_threshold:
            return gzip.compress(payload)
        return payload

    def _send_with_retry(
        self, endpoint: str, payload: dict[str, Any], signal_type: str = "trace"
    ) -> None:
        """Send payload with retry logic and exponential backoff."""
        if not self.enabled:
            return

        try:
            # Serialize payload
            payload_bytes = json.dumps(payload).encode("utf-8")

            # Compress if needed
            original_size = len(payload_bytes)
            payload_bytes = self._compress_payload(payload_bytes)
            compressed = len(payload_bytes) < original_size

            # Prepare headers
            headers = {"Content-Type": "application/json"}
            if compressed:
                headers["Content-Encoding"] = "gzip"

            # Verbose mode logging
            if self.verbose:
                print(f"\n[Telemetry] Sending {signal_type}")
                print(f"  Endpoint: {endpoint}")
                print(f"  Size: {len(payload_bytes)} bytes (compressed: {compressed})")
                print(f"  Payload preview: {json.dumps(payload, indent=2)[:200]}...\n")

            # Retry loop with exponential backoff
            last_exception = None
            for attempt in range(self.config.max_retries + 1):
                try:
                    request = Request(endpoint, data=payload_bytes, headers=headers)

                    with urlopen(request, timeout=self.timeout) as response:
                        if response.status == 200:
                            return  # Success
                        elif response.status >= 500:
                            # Server error - retry
                            last_exception = Exception(f"Server error: {response.status}")
                        else:
                            # Client error - don't retry
                            logger.debug(
                                f"Telemetry {signal_type} failed with status {response.status}"
                            )
                            return

                except (URLError, HTTPError, TimeoutError) as e:
                    last_exception = e
                    # Check if we should retry
                    if isinstance(e, HTTPError) and e.code < 500:
                        # Client error - don't retry
                        logger.debug(f"Telemetry {signal_type} failed: {e}")
                        return

                # Wait before retry (exponential backoff)
                if attempt < self.config.max_retries:
                    backoff_time = self.config.retry_backoff_base * (2**attempt)
                    time.sleep(backoff_time)

            # All retries exhausted
            if last_exception:
                logger.debug(
                    f"Telemetry {signal_type} failed after {self.config.max_retries} retries: {last_exception}"
                )

        except Exception as e:
            # Log any other errors in debug mode
            logger.debug(f"Telemetry {signal_type} error: {e}")

    def _get_resource_attributes(self) -> list[dict[str, Any]]:
        """Get common resource attributes for OTLP payloads."""
        return [
            {
                "key": "service.name",
                "value": {"stringValue": self.project_name},
            },
            {
                "key": "service.version",
                "value": {"stringValue": self.project_version},
            },
            {
                "key": "service.organization",
                "value": {"stringValue": self.organization},
            },
            {
                "key": "user.id",
                "value": {"stringValue": self.user_id},
            },
            {
                "key": "session.id",
                "value": {"stringValue": self.session_id},
            },
            {
                "key": "telemetry.sdk.name",
                "value": {"stringValue": "automagik-telemetry"},
            },
            {
                "key": "telemetry.sdk.version",
                "value": {"stringValue": "0.2.0"},
            },
        ]

    def _send_trace(self, event_type: str, data: dict[str, Any]) -> None:
        """Send trace (span) using OTLP traces format."""
        if not self.enabled:
            return

        # Generate trace and span IDs
        trace_id = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"  # 32 chars
        span_id = f"{uuid.uuid4().hex[:16]}"  # 16 chars

        # Create OTLP-compatible payload
        span = {
            "traceId": trace_id,
            "spanId": span_id,
            "name": event_type,
            "kind": "SPAN_KIND_INTERNAL",
            "startTimeUnixNano": int(time.time() * 1_000_000_000),
            "endTimeUnixNano": int(time.time() * 1_000_000_000),
            "attributes": self._create_attributes(data),
            "status": {"code": "STATUS_CODE_OK"},
        }

        # Queue or send immediately
        if self.config.batch_size > 1:
            with self._queue_lock:
                self._trace_queue.append(span)
                if len(self._trace_queue) >= self.config.batch_size:
                    self._flush_traces()
        else:
            self._flush_traces([span])

    def _send_metric(
        self,
        metric_name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Send metric using OTLP metrics format."""
        if not self.enabled:
            return

        timestamp_nano = int(time.time() * 1_000_000_000)
        attrs = self._create_attributes(attributes or {}, include_system=False)

        # Create data point based on metric type
        metric_data: dict[str, Any]
        if metric_type == MetricType.GAUGE:
            data_point = {
                "asDouble": value,
                "timeUnixNano": timestamp_nano,
                "attributes": attrs,
            }
            metric_data = {"gauge": {"dataPoints": [data_point]}}
        elif metric_type == MetricType.COUNTER:
            data_point = {
                "asDouble": value,
                "startTimeUnixNano": timestamp_nano,
                "timeUnixNano": timestamp_nano,
                "attributes": attrs,
            }
            metric_data = {
                "sum": {
                    "dataPoints": [data_point],
                    "isMonotonic": True,
                    "aggregationTemporality": 2,
                }
            }
        elif metric_type == MetricType.HISTOGRAM:
            data_point = {
                "count": 1,
                "sum": value,
                "startTimeUnixNano": timestamp_nano,
                "timeUnixNano": timestamp_nano,
                "attributes": attrs,
            }
            metric_data = {"histogram": {"dataPoints": [data_point], "aggregationTemporality": 2}}
        else:
            logger.debug(f"Unknown metric type: {metric_type}")
            return

        metric = {
            "name": metric_name,
            "description": "",
            **metric_data,
        }

        # Queue or send immediately
        if self.config.batch_size > 1:
            with self._queue_lock:
                self._metric_queue.append(metric)
                if len(self._metric_queue) >= self.config.batch_size:
                    self._flush_metrics()
        else:
            self._flush_metrics([metric])

    def _send_log(
        self,
        message: str,
        severity: LogSeverity = LogSeverity.INFO,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Send log using OTLP logs format."""
        if not self.enabled:
            return

        timestamp_nano = int(time.time() * 1_000_000_000)
        attrs = self._create_attributes(attributes or {}, include_system=False)

        log_record = {
            "timeUnixNano": timestamp_nano,
            "severityNumber": severity.value,
            "severityText": severity.name,
            "body": {"stringValue": message[:1000]},  # Truncate long messages
            "attributes": attrs,
        }

        # Queue or send immediately
        if self.config.batch_size > 1:
            with self._queue_lock:
                self._log_queue.append(log_record)
                if len(self._log_queue) >= self.config.batch_size:
                    self._flush_logs()
        else:
            self._flush_logs([log_record])

    def _flush_traces(self, spans: list[dict[str, Any]] | None = None) -> None:
        """Flush trace queue to endpoint."""
        if spans is None:
            with self._queue_lock:
                if not self._trace_queue:
                    return
                spans = list(self._trace_queue)
                self._trace_queue.clear()

        payload = {
            "resourceSpans": [
                {
                    "resource": {"attributes": self._get_resource_attributes()},
                    "scopeSpans": [
                        {
                            "scope": {
                                "name": f"{self.project_name}.telemetry",
                                "version": self.project_version,
                            },
                            "spans": spans,
                        }
                    ],
                }
            ]
        }

        self._send_with_retry(self.endpoint, payload, "trace")

    def _flush_metrics(self, metrics: list[dict[str, Any]] | None = None) -> None:
        """Flush metric queue to endpoint."""
        if metrics is None:
            with self._queue_lock:
                if not self._metric_queue:
                    return
                metrics = list(self._metric_queue)
                self._metric_queue.clear()

        payload = {
            "resourceMetrics": [
                {
                    "resource": {"attributes": self._get_resource_attributes()},
                    "scopeMetrics": [
                        {
                            "scope": {
                                "name": f"{self.project_name}.telemetry",
                                "version": self.project_version,
                            },
                            "metrics": metrics,
                        }
                    ],
                }
            ]
        }

        self._send_with_retry(self.metrics_endpoint, payload, "metric")

    def _flush_logs(self, log_records: list[dict[str, Any]] | None = None) -> None:
        """Flush log queue to endpoint."""
        if log_records is None:
            with self._queue_lock:
                if not self._log_queue:
                    return
                log_records = list(self._log_queue)
                self._log_queue.clear()

        payload = {
            "resourceLogs": [
                {
                    "resource": {"attributes": self._get_resource_attributes()},
                    "scopeLogs": [
                        {
                            "scope": {
                                "name": f"{self.project_name}.telemetry",
                                "version": self.project_version,
                            },
                            "logRecords": log_records,
                        }
                    ],
                }
            ]
        }

        self._send_with_retry(self.logs_endpoint, payload, "log")

    def _send_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Send telemetry event (legacy method - uses traces)."""
        self._send_trace(event_type, data)

    # === Public API ===

    def track_event(self, event_name: str, attributes: dict[str, Any] | None = None) -> None:
        """
        Track a telemetry event.

        Args:
            event_name: Event name (use StandardEvents constants)
            attributes: Event attributes (automatically sanitized for privacy)

        Example:
            >>> telemetry.track_event(StandardEvents.FEATURE_USED, {
            ...     "feature_name": "list_contacts",
            ...     "feature_category": "api_endpoint"
            ... })
        """
        self._send_event(event_name, attributes or {})

    def track_error(self, error: Exception, context: dict[str, Any] | None = None) -> None:
        """
        Track an error with context.

        Args:
            error: The exception that occurred
            context: Additional context about the error

        Example:
            >>> try:
            ...     risky_operation()
            ... except Exception as e:
            ...     telemetry.track_error(e, {
            ...         "error_code": "OMNI-1001",
            ...         "operation": "message_send"
            ...     })
        """
        data = {
            "error_type": type(error).__name__,
            "error_message": str(error)[:500],  # Truncate long errors
            **(context or {}),
        }
        self._send_event("automagik.error", data)

    def track_metric(
        self,
        metric_name: str,
        value: float,
        metric_type: MetricType | str = MetricType.GAUGE,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """
        Track a numeric metric using OTLP metrics format.

        Args:
            metric_name: Metric name
            value: Metric value
            metric_type: Type of metric (gauge, counter, or histogram) - default: GAUGE
            attributes: Metric attributes

        Example:
            >>> from automagik_telemetry import MetricType
            >>> telemetry.track_metric(
            ...     "api.latency",
            ...     123.45,
            ...     MetricType.HISTOGRAM,
            ...     {"endpoint": "/v1/contacts"}
            ... )
            >>>
            >>> # Using default GAUGE type
            >>> telemetry.track_metric("cpu.usage", 75.5, attributes={"core": "0"})
        """
        # Convert string to enum if needed
        if isinstance(metric_type, str):
            try:
                metric_type = MetricType(metric_type.lower())
            except ValueError:
                metric_type = MetricType.GAUGE

        self._send_metric(metric_name, value, metric_type, attributes)

    def track_log(
        self,
        message: str,
        severity: LogSeverity | str = LogSeverity.INFO,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """
        Track a log message using OTLP logs format.

        Args:
            message: Log message
            severity: Log severity level (TRACE, DEBUG, INFO, WARN, ERROR, FATAL)
            attributes: Additional log attributes

        Example:
            >>> from automagik_telemetry import LogSeverity
            >>> telemetry.track_log(
            ...     "User authentication successful",
            ...     severity=LogSeverity.INFO,
            ...     attributes={"user_id": "anonymous-uuid"}
            ... )
        """
        # Convert string to enum if needed
        if isinstance(severity, str):
            try:
                severity = LogSeverity[severity.upper()]
            except KeyError:
                severity = LogSeverity.INFO

        self._send_log(message, severity, attributes)

    def flush(self) -> None:
        """
        Manually flush all queued events to the telemetry endpoint.

        This is useful when you want to ensure all events are sent before
        the application exits or at specific checkpoints.

        Example:
            >>> telemetry.track_event("app.shutdown")
            >>> telemetry.flush()  # Ensure event is sent before exit
        """
        if not self.enabled:
            return

        # Flush all queues
        self._flush_traces()
        self._flush_metrics()
        self._flush_logs()

    # === Control Methods ===

    def enable(self) -> None:
        """Enable telemetry and save preference."""
        self.enabled = True
        # Remove opt-out file if it exists
        opt_out_file = Path.home() / ".automagik-no-telemetry"
        if opt_out_file.exists():
            try:
                opt_out_file.unlink()
            except Exception:
                pass

    def disable(self) -> None:
        """Disable telemetry permanently."""
        self.enabled = False
        # Create opt-out file
        try:
            opt_out_file = Path.home() / ".automagik-no-telemetry"
            opt_out_file.touch()
        except Exception:
            pass

    def is_enabled(self) -> bool:
        """Check if telemetry is enabled."""
        return self.enabled

    def get_status(self) -> dict[str, Any]:
        """Get telemetry status information."""
        with self._queue_lock:
            queue_sizes = {
                "traces": len(self._trace_queue),
                "metrics": len(self._metric_queue),
                "logs": len(self._log_queue),
            }

        return {
            "enabled": self.enabled,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "project_name": self.project_name,
            "project_version": self.project_version,
            "endpoint": self.endpoint,
            "metrics_endpoint": self.metrics_endpoint,
            "logs_endpoint": self.logs_endpoint,
            "opt_out_file_exists": (Path.home() / ".automagik-no-telemetry").exists(),
            "env_var": os.getenv("AUTOMAGIK_TELEMETRY_ENABLED"),
            "verbose": self.verbose,
            "batch_size": self.config.batch_size,
            "compression_enabled": self.config.compression_enabled,
            "queue_sizes": queue_sizes,
        }

    # === Async API Methods ===

    async def track_event_async(
        self, event_name: str, attributes: dict[str, Any] | None = None
    ) -> None:
        """
        Async version of track_event for use in async contexts.

        This method allows tracking events from asyncio applications without blocking
        the event loop. It runs the synchronous track_event method in a thread pool.

        Args:
            event_name: Event name (use StandardEvents constants)
            attributes: Event attributes (automatically sanitized for privacy)

        Example:
            >>> import asyncio
            >>> from automagik_telemetry import AutomagikTelemetry, StandardEvents
            >>>
            >>> telemetry = AutomagikTelemetry(project_name="my-app", version="1.0.0")
            >>>
            >>> async def main():
            ...     await telemetry.track_event_async(StandardEvents.FEATURE_USED, {
            ...         "feature_name": "async_feature"
            ...     })
            >>>
            >>> asyncio.run(main())
        """
        await asyncio.to_thread(self.track_event, event_name, attributes)

    async def track_error_async(
        self, error: Exception, context: dict[str, Any] | None = None
    ) -> None:
        """
        Async version of track_error for use in async contexts.

        This method allows tracking errors from asyncio applications without blocking
        the event loop. It runs the synchronous track_error method in a thread pool.

        Args:
            error: The exception that occurred
            context: Additional context about the error

        Example:
            >>> import asyncio
            >>> from automagik_telemetry import AutomagikTelemetry
            >>>
            >>> telemetry = AutomagikTelemetry(project_name="my-app", version="1.0.0")
            >>>
            >>> async def main():
            ...     try:
            ...         raise ValueError("Test error")
            ...     except Exception as e:
            ...         await telemetry.track_error_async(e, {
            ...             "error_code": "TEST-001",
            ...             "operation": "test_operation"
            ...         })
            >>>
            >>> asyncio.run(main())
        """
        await asyncio.to_thread(self.track_error, error, context)

    async def track_metric_async(
        self,
        metric_name: str,
        value: float,
        metric_type: MetricType | str = MetricType.GAUGE,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """
        Async version of track_metric for use in async contexts.

        This method allows tracking metrics from asyncio applications without blocking
        the event loop. It runs the synchronous track_metric method in a thread pool.

        Args:
            metric_name: Metric name
            value: Metric value
            metric_type: Type of metric (gauge, counter, or histogram)
            attributes: Metric attributes

        Example:
            >>> import asyncio
            >>> from automagik_telemetry import AutomagikTelemetry, MetricType
            >>>
            >>> telemetry = AutomagikTelemetry(project_name="my-app", version="1.0.0")
            >>>
            >>> async def main():
            ...     await telemetry.track_metric_async(
            ...         "api.latency",
            ...         123.45,
            ...         MetricType.HISTOGRAM,
            ...         {"endpoint": "/v1/users"}
            ...     )
            >>>
            >>> asyncio.run(main())
        """
        await asyncio.to_thread(self.track_metric, metric_name, value, metric_type, attributes)

    async def track_log_async(
        self,
        message: str,
        severity: LogSeverity | str = LogSeverity.INFO,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """
        Async version of track_log for use in async contexts.

        This method allows tracking logs from asyncio applications without blocking
        the event loop. It runs the synchronous track_log method in a thread pool.

        Args:
            message: Log message
            severity: Log severity level (TRACE, DEBUG, INFO, WARN, ERROR, FATAL)
            attributes: Additional log attributes

        Example:
            >>> import asyncio
            >>> from automagik_telemetry import AutomagikTelemetry, LogSeverity
            >>>
            >>> telemetry = AutomagikTelemetry(project_name="my-app", version="1.0.0")
            >>>
            >>> async def main():
            ...     await telemetry.track_log_async(
            ...         "User authentication successful",
            ...         LogSeverity.INFO,
            ...         {"user_id": "anonymous-uuid"}
            ...     )
            >>>
            >>> asyncio.run(main())
        """
        await asyncio.to_thread(self.track_log, message, severity, attributes)

    async def flush_async(self) -> None:
        """
        Async version of flush for use in async contexts.

        This method allows flushing all queued events from asyncio applications
        without blocking the event loop. It runs the synchronous flush method
        in a thread pool.

        Example:
            >>> import asyncio
            >>> from automagik_telemetry import AutomagikTelemetry
            >>>
            >>> telemetry = AutomagikTelemetry(project_name="my-app", version="1.0.0")
            >>>
            >>> async def main():
            ...     await telemetry.track_event_async("app.startup")
            ...     await telemetry.flush_async()  # Ensure event is sent
            >>>
            >>> asyncio.run(main())
        """
        await asyncio.to_thread(self.flush)

    def __del__(self) -> None:
        """Cleanup: flush queued events and stop background timer."""
        try:
            self._shutdown = True

            # Cancel flush timer
            if self._flush_timer is not None:
                self._flush_timer.cancel()

            # Flush all remaining events
            self.flush()
        except Exception:
            # Silent failure during cleanup
            pass


# Backwards compatibility alias
# Note: TelemetryClient is deprecated and will be removed in a future version.
# Please use AutomagikTelemetry instead.
TelemetryClient = AutomagikTelemetry
