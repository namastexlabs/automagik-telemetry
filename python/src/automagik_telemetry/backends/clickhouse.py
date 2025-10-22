"""
Direct ClickHouse backend for telemetry data.

Bypasses the OpenTelemetry Collector and writes directly to ClickHouse HTTP API.
Uses only standard library - no external dependencies.
"""

import gzip
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class ClickHouseBackend:
    """
    Direct ClickHouse insertion backend.

    Transforms OTLP-format traces to our custom ClickHouse schema
    and inserts via HTTP API.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:8123",
        database: str = "telemetry",
        table: str = "traces",
        username: str = "default",
        password: str = "",
        timeout: int = 5,
        batch_size: int = 100,
        compression_enabled: bool = True,
        max_retries: int = 3,
    ):
        """
        Initialize ClickHouse backend.

        Args:
            endpoint: ClickHouse HTTP endpoint (e.g. http://localhost:8123)
            database: Database name (default: telemetry)
            table: Table name (default: traces)
            username: ClickHouse username (default: default)
            password: ClickHouse password
            timeout: HTTP timeout in seconds
            batch_size: Number of rows to batch before inserting
            compression_enabled: Enable gzip compression
            max_retries: Maximum retry attempts
        """
        self.endpoint = endpoint.rstrip("/")
        self.database = database
        self.table = table
        self.username = username
        self.password = password
        self.timeout = timeout
        self.batch_size = batch_size
        self.compression_enabled = compression_enabled
        self.max_retries = max_retries

        self._batch: list[dict[str, Any]] = []

    def transform_otlp_to_clickhouse(self, otlp_span: dict[str, Any]) -> dict[str, Any]:
        """
        Transform OTLP span format to our ClickHouse schema.

        Args:
            otlp_span: OTLP-formatted span data

        Returns:
            Dict matching our ClickHouse traces table schema
        """
        # Extract timestamp (use start time or current time)
        timestamp_ns = otlp_span.get("startTimeUnixNano", time.time_ns())
        timestamp = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc)

        # Calculate duration in milliseconds
        start_ns = otlp_span.get("startTimeUnixNano", 0)
        end_ns = otlp_span.get("endTimeUnixNano", start_ns)
        duration_ms = int((end_ns - start_ns) / 1_000_000) if end_ns > start_ns else 0

        # Extract status
        status = otlp_span.get("status", {})
        status_code = "OK" if status.get("code") == 1 else status.get("message", "OK")

        # Transform attributes from OTLP format to flat dict
        attributes = {}
        for attr in otlp_span.get("attributes", []):
            key = attr.get("key", "")
            value = attr.get("value", {})

            # Extract value based on type
            if "stringValue" in value:
                attributes[key] = value["stringValue"]
            elif "intValue" in value:
                attributes[key] = str(value["intValue"])
            elif "doubleValue" in value:
                attributes[key] = str(value["doubleValue"])
            elif "boolValue" in value:
                attributes[key] = str(value["boolValue"])

        # Extract resource attributes
        resource_attrs = {}
        for attr in otlp_span.get("resource", {}).get("attributes", []):
            key = attr.get("key", "")
            value = attr.get("value", {})
            if "stringValue" in value:
                resource_attrs[key] = value["stringValue"]

        # Build ClickHouse row
        return {
            "trace_id": otlp_span.get("traceId", ""),
            "span_id": otlp_span.get("spanId", ""),
            "parent_span_id": otlp_span.get("parentSpanId", ""),
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_ns": timestamp_ns,
            "duration_ms": duration_ms,
            "service_name": resource_attrs.get("service.name", "unknown"),
            "span_name": otlp_span.get("name", "unknown"),
            "span_kind": otlp_span.get("kind", "INTERNAL"),
            "status_code": status_code,
            "status_message": status.get("message", ""),
            "project_name": resource_attrs.get("project.name", ""),
            "project_version": resource_attrs.get("project.version", ""),
            "environment": resource_attrs.get("deployment.environment", "production"),
            "hostname": resource_attrs.get("host.name", ""),
            "attributes": attributes,
            "user_id": attributes.get("user.id", ""),
            "session_id": attributes.get("session.id", ""),
            "os_type": resource_attrs.get("os.type", ""),
            "os_version": resource_attrs.get("os.version", ""),
            "runtime_name": resource_attrs.get("process.runtime.name", ""),
            "runtime_version": resource_attrs.get("process.runtime.version", ""),
        }

    def add_to_batch(self, otlp_span: dict[str, Any]) -> None:
        """
        Add a span to the batch queue.

        Args:
            otlp_span: OTLP-formatted span data
        """
        row = self.transform_otlp_to_clickhouse(otlp_span)
        self._batch.append(row)

        # Auto-flush if batch size reached
        if len(self._batch) >= self.batch_size:
            self.flush()

    def flush(self) -> bool:
        """
        Flush the current batch to ClickHouse.

        Returns:
            True if successful, False otherwise
        """
        if not self._batch:
            return True

        try:
            return self._insert_batch(self._batch)
        finally:
            self._batch.clear()

    def _insert_batch(self, rows: list[dict[str, Any]]) -> bool:
        """
        Insert a batch of rows into ClickHouse.

        Args:
            rows: List of rows to insert

        Returns:
            True if successful, False otherwise
        """
        if not rows:
            return True

        # Convert rows to JSONEachRow format (one JSON object per line)
        data = "\n".join(json.dumps(row) for row in rows).encode("utf-8")

        # Compress if enabled and data is large enough
        if self.compression_enabled and len(data) > 1024:
            data = gzip.compress(data)
            content_encoding = "gzip"
        else:
            content_encoding = None

        # Build URL with query
        query = f"INSERT INTO {self.database}.{self.table} FORMAT JSONEachRow"
        url = f"{self.endpoint}/?query={query}"

        # Add authentication if provided
        if self.username:
            auth_string = f"{self.username}:{self.password}".encode("utf-8")
            import base64

            auth_header = b"Basic " + base64.b64encode(auth_string)
        else:
            auth_header = None

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                headers = {"Content-Type": "application/x-ndjson"}
                if content_encoding:
                    headers["Content-Encoding"] = content_encoding
                if auth_header:
                    headers["Authorization"] = auth_header.decode("utf-8")

                request = Request(url, data=data, headers=headers, method="POST")

                with urlopen(request, timeout=self.timeout) as response:
                    if response.status == 200:
                        logger.debug(
                            f"Inserted {len(rows)} rows to ClickHouse successfully"
                        )
                        return True
                    else:
                        logger.warning(
                            f"ClickHouse returned status {response.status}: {response.read().decode('utf-8')}"
                        )

            except HTTPError as e:
                logger.error(
                    f"HTTP error inserting to ClickHouse (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                    continue

            except URLError as e:
                logger.error(
                    f"Network error inserting to ClickHouse (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)
                    continue

            except Exception as e:
                logger.error(f"Unexpected error inserting to ClickHouse: {e}")
                break

        return False

    def send_trace(self, otlp_span: dict[str, Any]) -> bool:
        """
        Send a single trace span to ClickHouse.

        This is a convenience method that batches internally.

        Args:
            otlp_span: OTLP-formatted span data

        Returns:
            True if added to batch successfully
        """
        try:
            self.add_to_batch(otlp_span)
            return True
        except Exception as e:
            logger.error(f"Error adding span to batch: {e}")
            return False
