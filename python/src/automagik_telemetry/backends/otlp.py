"""
OTLP backend for telemetry data.

Sends traces, metrics, and logs using the OpenTelemetry Protocol (OTLP) over HTTP.
Uses only standard library - no external dependencies.
"""

import gzip
import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import TelemetryBackend

logger = logging.getLogger(__name__)


class OTLPBackend(TelemetryBackend):
    """
    OTLP HTTP backend for sending telemetry data.

    Sends OTLP-formatted traces, metrics, and logs to OpenTelemetry collectors
    using HTTP/JSON with optional gzip compression and retry logic.
    """

    def __init__(
        self,
        endpoint: str,
        metrics_endpoint: str,
        logs_endpoint: str,
        timeout: int = 5,
        max_retries: int = 3,
        retry_backoff_base: float = 1.0,
        compression_enabled: bool = True,
        compression_threshold: int = 1024,
        verbose: bool = False,
    ):
        """
        Initialize OTLP backend.

        Args:
            endpoint: OTLP traces endpoint (e.g., https://telemetry.namastex.ai/v1/traces)
            metrics_endpoint: OTLP metrics endpoint (e.g., https://telemetry.namastex.ai/v1/metrics)
            logs_endpoint: OTLP logs endpoint (e.g., https://telemetry.namastex.ai/v1/logs)
            timeout: HTTP timeout in seconds (default: 5)
            max_retries: Maximum number of retry attempts (default: 3)
            retry_backoff_base: Base backoff time in seconds (default: 1.0)
            compression_enabled: Enable gzip compression (default: True)
            compression_threshold: Minimum payload size for compression in bytes (default: 1024)
            verbose: Enable verbose logging (default: False)
        """
        self.endpoint = endpoint
        self.metrics_endpoint = metrics_endpoint
        self.logs_endpoint = logs_endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.compression_enabled = compression_enabled
        self.compression_threshold = compression_threshold
        self.verbose = verbose

    def _compress_payload(self, payload: bytes) -> bytes:
        """
        Compress payload using gzip if it exceeds threshold.

        Args:
            payload: Raw bytes to compress

        Returns:
            Compressed or original payload
        """
        if self.compression_enabled and len(payload) >= self.compression_threshold:
            return gzip.compress(payload)
        return payload

    def _send_with_retry(
        self, endpoint: str, payload: dict[str, Any], signal_type: str = "trace"
    ) -> bool:
        """
        Send payload with retry logic and exponential backoff.

        Args:
            endpoint: Target endpoint URL
            payload: OTLP payload to send
            signal_type: Type of signal (trace, metric, log) for logging

        Returns:
            True if successful, False otherwise
        """
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
            for attempt in range(self.max_retries + 1):
                try:
                    request = Request(endpoint, data=payload_bytes, headers=headers)

                    with urlopen(request, timeout=self.timeout) as response:
                        if response.status == 200:
                            logger.debug(f"OTLP {signal_type} sent successfully")
                            return True
                        elif response.status >= 500:
                            # Server error - retry
                            last_exception = Exception(f"Server error: {response.status}")
                        else:
                            # Client error - don't retry
                            logger.debug(
                                f"Telemetry {signal_type} failed with status {response.status}"
                            )
                            return False

                except (URLError, HTTPError, TimeoutError) as e:
                    last_exception = e
                    # Check if we should retry
                    if isinstance(e, HTTPError) and e.code < 500:
                        # Client error - don't retry
                        logger.debug(f"Telemetry {signal_type} failed: {e}")
                        return False

                # Wait before retry (exponential backoff)
                if attempt < self.max_retries:
                    backoff_time = self.retry_backoff_base * (2**attempt)
                    time.sleep(backoff_time)

            # All retries exhausted
            if last_exception:
                logger.debug(
                    f"Telemetry {signal_type} failed after {self.max_retries} retries: {last_exception}"
                )
            return False

        except Exception as e:
            # Log any other errors in debug mode
            logger.debug(f"Telemetry {signal_type} error: {e}")
            return False

    def send_trace(self, otlp_payload: dict[str, Any]) -> bool:
        """
        Send an OTLP trace payload to the traces endpoint.

        Args:
            otlp_payload: OTLP-formatted trace payload with resourceSpans structure

        Returns:
            True if successful, False otherwise
        """
        return self._send_with_retry(self.endpoint, otlp_payload, "trace")

    def send_metric(self, otlp_payload: dict[str, Any]) -> bool:
        """
        Send an OTLP metric payload to the metrics endpoint.

        Args:
            otlp_payload: OTLP-formatted metric payload with resourceMetrics structure

        Returns:
            True if successful, False otherwise
        """
        return self._send_with_retry(self.metrics_endpoint, otlp_payload, "metric")

    def send_log(self, otlp_payload: dict[str, Any]) -> bool:
        """
        Send an OTLP log payload to the logs endpoint.

        Args:
            otlp_payload: OTLP-formatted log payload with resourceLogs structure

        Returns:
            True if successful, False otherwise
        """
        return self._send_with_retry(self.logs_endpoint, otlp_payload, "log")

    def flush(self) -> bool:
        """
        Flush any pending data.

        Note: OTLP backend sends data immediately, so this is a no-op.
        Included for consistency with other backends.

        Returns:
            True (always succeeds since OTLP doesn't buffer)
        """
        return True
