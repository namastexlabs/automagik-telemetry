"""
Abstract Base Class for telemetry backends.

Defines the contract that all telemetry backends must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class TelemetryBackend(ABC):
    """
    Abstract base class for telemetry backends.

    All telemetry backends must implement this interface to ensure consistent
    behavior across different storage systems (OTLP, ClickHouse, etc.).

    The backend is responsible for:
    - Sending trace spans to the storage system
    - Sending metrics to the storage system
    - Sending logs to the storage system
    - Flushing any pending/buffered data

    Implementations should handle:
    - Network errors and retries
    - Data serialization/formatting
    - Batching and buffering (if applicable)
    - Authentication and authorization
    """

    @abstractmethod
    def send_trace(self, payload: dict[str, Any]) -> bool:  # pragma: no cover
        """
        Send a trace span to the backend.

        Args:
            payload: Trace payload in the backend's expected format.
                     For OTLP backends, this is OTLP-formatted span data.
                     For ClickHouse backends, this can be OTLP or native format.

        Returns:
            True if the trace was sent successfully (or queued for sending),
            False if the operation failed.

        Note:
            This method should handle retries internally and only return False
            if all retry attempts are exhausted or a fatal error occurs.
        """
        pass

    @abstractmethod
    def send_metric(self, payload: dict[str, Any], **kwargs: Any) -> bool:  # pragma: no cover
        """
        Send a metric to the backend.

        Args:
            payload: Metric payload in the backend's expected format.
                     For OTLP backends, this is OTLP-formatted metric data.
                     For ClickHouse backends, this can be OTLP or native format.
            **kwargs: Additional backend-specific parameters (e.g., metric_name, value, etc.)

        Returns:
            True if the metric was sent successfully (or queued for sending),
            False if the operation failed.

        Note:
            This method should handle retries internally and only return False
            if all retry attempts are exhausted or a fatal error occurs.
        """
        pass

    @abstractmethod
    def send_log(self, payload: dict[str, Any], **kwargs: Any) -> bool:  # pragma: no cover
        """
        Send a log entry to the backend.

        Args:
            payload: Log payload in the backend's expected format.
                     For OTLP backends, this is OTLP-formatted log data.
                     For ClickHouse backends, this can be OTLP or native format.
            **kwargs: Additional backend-specific parameters (e.g., message, level, etc.)

        Returns:
            True if the log was sent successfully (or queued for sending),
            False if the operation failed.

        Note:
            This method should handle retries internally and only return False
            if all retry attempts are exhausted or a fatal error occurs.
        """
        pass

    @abstractmethod
    def flush(self) -> bool:  # pragma: no cover
        """
        Flush any pending/buffered data to the backend.

        This method should:
        - Send all queued/batched data immediately
        - Block until all data is sent (or max retries exhausted)
        - Clear internal buffers after flushing

        For backends that send data immediately (like OTLP), this can be a no-op.
        For backends that batch data (like ClickHouse), this sends all pending batches.

        Returns:
            True if all data was flushed successfully, False if any flush operation failed.
            For backends without buffering (like OTLP), this typically returns True.

        Note:
            This method is called during shutdown to ensure no data is lost.
            It should be safe to call multiple times.
        """
        pass
