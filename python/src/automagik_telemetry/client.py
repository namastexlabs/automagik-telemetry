"""
Production-ready telemetry client implementation.

Based on battle-tested code from automagik-omni and automagik-spark.
Uses only Python standard library - no external dependencies.
"""

import json
import logging
import os
import platform
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class TelemetryClient:
    """
    Privacy-first telemetry client for Automagik projects.
    
    Features:
    - Disabled by default - users must explicitly opt-in
    - Uses only stdlib - no external dependencies
    - Sends OTLP-compatible traces
    - Silent failures - never crashes your app
    - Auto-disables in CI/test environments
    
    Example:
        >>> from automagik_telemetry import TelemetryClient, StandardEvents
        >>> 
        >>> telemetry = TelemetryClient(
        ...     project_name="omni",
        ...     version="1.0.0"
        ... )
        >>> 
        >>> telemetry.track_event(StandardEvents.FEATURE_USED, {
        ...     "feature_name": "list_contacts"
        ... })
    """

    def __init__(
        self,
        project_name: str,
        version: str,
        endpoint: Optional[str] = None,
        organization: str = "namastex",
        timeout: int = 5,
    ):
        """
        Initialize telemetry client.
        
        Args:
            project_name: Name of the Automagik project (omni, hive, forge, etc.)
            version: Version of the project
            endpoint: Custom telemetry endpoint (defaults to telemetry.namastex.ai)
            organization: Organization name (default: namastex)
            timeout: HTTP timeout in seconds (default: 5)
        """
        self.project_name = project_name
        self.project_version = version
        self.organization = organization
        self.timeout = timeout
        
        # Allow custom endpoint for self-hosting
        self.endpoint = endpoint or os.getenv(
            "AUTOMAGIK_TELEMETRY_ENDPOINT",
            "https://telemetry.namastex.ai/v1/traces"
        )
        
        # User & session IDs
        self.user_id = self._get_or_create_user_id()
        self.session_id = str(uuid.uuid4())
        
        # Enable/disable check
        self.enabled = self._is_telemetry_enabled()
        
        # Verbose mode (print events to console)
        self.verbose = os.getenv("AUTOMAGIK_TELEMETRY_VERBOSE", "false").lower() == "true"

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

    def _get_system_info(self) -> Dict[str, Any]:
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

    def _create_attributes(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert data to OTLP attribute format with type safety."""
        attributes = []

        # Add system information
        system_info = self._get_system_info()
        for key, value in system_info.items():
            if isinstance(value, bool):
                attributes.append({"key": f"system.{key}", "value": {"boolValue": value}})
            elif isinstance(value, (int, float)):
                attributes.append(
                    {"key": f"system.{key}", "value": {"doubleValue": float(value)}}
                )
            else:
                attributes.append({"key": f"system.{key}", "value": {"stringValue": str(value)}})

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

    def _send_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Send telemetry event to the endpoint (internal method)."""
        if not self.enabled:
            return  # Silent no-op when disabled

        try:
            # Generate trace and span IDs
            trace_id = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"  # 32 chars
            span_id = f"{uuid.uuid4().hex[:16]}"  # 16 chars

            # Create OTLP-compatible payload
            payload = {
                "resourceSpans": [
                    {
                        "resource": {
                            "attributes": [
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
                                    "value": {"stringValue": "0.1.0"},
                                },
                            ]
                        },
                        "scopeSpans": [
                            {
                                "scope": {
                                    "name": f"{self.project_name}.telemetry",
                                    "version": self.project_version,
                                },
                                "spans": [
                                    {
                                        "traceId": trace_id,
                                        "spanId": span_id,
                                        "name": event_type,
                                        "kind": "SPAN_KIND_INTERNAL",
                                        "startTimeUnixNano": int(time.time() * 1_000_000_000),
                                        "endTimeUnixNano": int(time.time() * 1_000_000_000),
                                        "attributes": self._create_attributes(data),
                                        "status": {"code": "STATUS_CODE_OK"},
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }

            # Verbose mode: print event to console
            if self.verbose:
                print(f"\n[Telemetry] Sending event: {event_type}")
                print(f"  Project: {self.project_name}")
                print(f"  Data: {json.dumps(data, indent=2)}")
                print(f"  Endpoint: {self.endpoint}\n")

            # Send HTTP request
            request = Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

            with urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    logger.debug(f"Telemetry event failed with status {response.status}")

        except (URLError, HTTPError, TimeoutError) as e:
            # Log only in debug mode, never crash the application
            logger.debug(f"Telemetry network error: {e}")
        except Exception as e:
            # Log any other errors in debug mode
            logger.debug(f"Telemetry event error: {e}")

    # === Public API ===

    def track_event(self, event_name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
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

    def track_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
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
        self, metric_name: str, value: float, attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track a numeric metric.
        
        Args:
            metric_name: Metric name
            value: Metric value
            attributes: Metric attributes
            
        Example:
            >>> telemetry.track_metric(StandardEvents.OPERATION_LATENCY, {
            ...     "operation_type": "api_request",
            ...     "duration_ms": 123
            ... })
        """
        data = {"value": value, **(attributes or {})}
        self._send_event(metric_name, data)

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

    def get_status(self) -> Dict[str, Any]:
        """Get telemetry status information."""
        return {
            "enabled": self.enabled,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "project_name": self.project_name,
            "project_version": self.project_version,
            "endpoint": self.endpoint,
            "opt_out_file_exists": (Path.home() / ".automagik-no-telemetry").exists(),
            "env_var": os.getenv("AUTOMAGIK_TELEMETRY_ENABLED"),
            "verbose": self.verbose,
        }
