"""
Direct ClickHouse backend for telemetry data.

Bypasses the OpenTelemetry Collector and writes directly to ClickHouse HTTP API.
Uses only standard library - no external dependencies.
"""

import gzip
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class ClickHouseBackend:
    """
    Direct ClickHouse insertion backend.

    Transforms OTLP-format traces, metrics, and logs to our custom ClickHouse schema
    and inserts via HTTP API.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:8123",
        database: str = "telemetry",
        traces_table: str = "traces",
        metrics_table: str = "metrics",
        logs_table: str = "logs",
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
            traces_table: Traces table name (default: traces)
            metrics_table: Metrics table name (default: metrics)
            logs_table: Logs table name (default: logs)
            username: ClickHouse username (default: default)
            password: ClickHouse password
            timeout: HTTP timeout in seconds
            batch_size: Number of rows to batch before inserting
            compression_enabled: Enable gzip compression
            max_retries: Maximum retry attempts
        """
        self.endpoint = endpoint.rstrip("/")
        self.database = database
        self.traces_table = traces_table
        self.metrics_table = metrics_table
        self.logs_table = logs_table
        self.username = username
        self.password = password
        self.timeout = timeout
        self.batch_size = batch_size
        self.compression_enabled = compression_enabled
        self.max_retries = max_retries

        # Separate batches for each telemetry type
        self._trace_batch: list[dict[str, Any]] = []
        self._metric_batch: list[dict[str, Any]] = []
        self._log_batch: list[dict[str, Any]] = []

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
        self._trace_batch.append(row)

        # Auto-flush if batch size reached
        if len(self._trace_batch) >= self.batch_size:
            self.flush()

    def flush(self) -> bool:
        """
        Flush all current batches to ClickHouse.

        Returns:
            True if all flushes successful, False otherwise
        """
        success = True

        # Flush traces
        if self._trace_batch:
            try:
                if not self._insert_batch(self._trace_batch, self.traces_table):
                    success = False
            finally:
                self._trace_batch.clear()

        # Flush metrics
        if self._metric_batch:
            try:
                if not self._insert_batch(self._metric_batch, self.metrics_table):
                    success = False
            finally:
                self._metric_batch.clear()

        # Flush logs
        if self._log_batch:
            try:
                if not self._insert_batch(self._log_batch, self.logs_table):
                    success = False
            finally:
                self._log_batch.clear()

        return success

    def _insert_batch(self, rows: list[dict[str, Any]], table_name: str) -> bool:
        """
        Insert a batch of rows into ClickHouse.

        Args:
            rows: List of rows to insert
            table_name: Target table name

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
        from urllib.parse import quote
        query = f"INSERT INTO {self.database}.{table_name} FORMAT JSONEachRow"
        url = f"{self.endpoint}/?query={quote(query)}"

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
                            f"Inserted {len(rows)} rows to ClickHouse table {table_name} successfully"
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

    def send_metric(
        self,
        metric_name: str,
        value: float,
        metric_type: str = "gauge",
        unit: str = "",
        attributes: dict[str, Any] | None = None,
        resource_attributes: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> bool:
        """
        Send a single metric to ClickHouse.

        Args:
            metric_name: Name of the metric (e.g., http.request.duration)
            value: Numeric value of the metric
            metric_type: Type of metric (gauge, counter, histogram, summary) - default: gauge
            unit: Unit of measurement (ms, bytes, requests, etc.)
            attributes: Metric-specific attributes/labels
            resource_attributes: Service/application resource attributes
            timestamp: Timestamp for the metric (default: now)

        Returns:
            True if added to batch successfully
        """
        try:
            # Default values
            if attributes is None:
                attributes = {}
            if resource_attributes is None:
                resource_attributes = {}
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)

            # Map COUNTER to SUM for ClickHouse enum compatibility
            clickhouse_type = metric_type.upper()
            if clickhouse_type == "COUNTER":
                clickhouse_type = "SUM"

            # Ensure valid enum value
            valid_types = ["GAUGE", "SUM", "HISTOGRAM", "EXPONENTIAL_HISTOGRAM", "SUMMARY"]
            if clickhouse_type not in valid_types:
                logger.warning(f"Invalid metric_type '{metric_type}', defaulting to GAUGE")
                clickhouse_type = "GAUGE"

            # Generate unique metric_id
            metric_id = str(uuid.uuid4())

            # Calculate timestamp_ns
            timestamp_ns = int(timestamp.timestamp() * 1_000_000_000)

            # Convert attributes to Map(String, String) format
            attrs_map = {str(k): str(v) for k, v in attributes.items()}

            # Determine if value is int or float
            is_int = isinstance(value, int) and not isinstance(value, bool)
            value_int = int(value) if is_int else 0
            value_double = 0.0 if is_int else float(value)

            # Build metric row matching ClickHouse schema
            metric_row = {
                "metric_id": metric_id,
                "metric_name": metric_name,
                "metric_type": clickhouse_type,
                "metric_unit": unit,
                "metric_description": "",
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp_ns": timestamp_ns,
                "time_window_start": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "time_window_end": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "value_int": value_int,
                "value_double": value_double,
                "is_monotonic": 1 if clickhouse_type == "SUM" else 0,
                "aggregation_temporality": "DELTA" if clickhouse_type == "SUM" else "UNSPECIFIED",
                "histogram_count": 0,
                "histogram_sum": 0.0,
                "histogram_min": 0.0,
                "histogram_max": 0.0,
                "histogram_bucket_counts": [],
                "histogram_explicit_bounds": [],
                "summary_count": 0,
                "summary_sum": 0.0,
                "quantile_values": {},
                "project_name": resource_attributes.get("project.name", ""),
                "project_version": resource_attributes.get("project.version", ""),
                "service_name": resource_attributes.get("service.name", "unknown"),
                "service_namespace": resource_attributes.get("service.namespace", ""),
                "service_instance_id": resource_attributes.get("service.instance.id", ""),
                "environment": resource_attributes.get("deployment.environment", "production"),
                "hostname": resource_attributes.get("host.name", ""),
                "attributes": attrs_map,
                "user_id": attributes.get("user.id", ""),
                "session_id": attributes.get("session.id", ""),
                "os_type": resource_attributes.get("os.type", ""),
                "os_version": resource_attributes.get("os.version", ""),
                "runtime_name": resource_attributes.get("process.runtime.name", ""),
                "runtime_version": resource_attributes.get("process.runtime.version", ""),
                "cloud_provider": resource_attributes.get("cloud.provider", ""),
                "cloud_region": resource_attributes.get("cloud.region", ""),
                "cloud_availability_zone": resource_attributes.get("cloud.availability_zone", ""),
                "instrumentation_library_name": resource_attributes.get("telemetry.sdk.name", ""),
                "instrumentation_library_version": resource_attributes.get("telemetry.sdk.version", ""),
                "schema_url": "",
            }

            # Add to batch
            self._metric_batch.append(metric_row)

            # Auto-flush if batch size reached
            if len(self._metric_batch) >= self.batch_size:
                self.flush()

            return True

        except Exception as e:
            logger.error(f"Error adding metric to batch: {e}", exc_info=True)
            return False

    def send_log(
        self,
        message: str,
        level: str = "INFO",
        attributes: dict[str, Any] | None = None,
        resource_attributes: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
        trace_id: str = "",
        span_id: str = "",
    ) -> bool:
        """
        Send a single log entry to ClickHouse.

        Args:
            message: The log message
            level: Severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            attributes: Log-specific attributes/context
            resource_attributes: Service/application resource attributes
            timestamp: Timestamp for the log (default: now)
            trace_id: Optional trace ID for correlation
            span_id: Optional span ID for correlation

        Returns:
            True if added to batch successfully
        """
        try:
            # Default values
            if attributes is None:
                attributes = {}
            if resource_attributes is None:
                resource_attributes = {}
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)

            # Generate unique log_id
            log_id = str(uuid.uuid4())

            # Calculate timestamps
            timestamp_ns = int(timestamp.timestamp() * 1_000_000_000)
            observed_timestamp = datetime.now(timezone.utc)
            observed_timestamp_ns = int(observed_timestamp.timestamp() * 1_000_000_000)

            # Map severity levels to OTLP standard numbers
            severity_map = {
                "TRACE": (1, 1),
                "DEBUG": (5, 5),
                "INFO": (9, 9),
                "WARN": (13, 13),
                "WARNING": (13, 13),
                "ERROR": (17, 17),
                "CRITICAL": (21, 21),
                "FATAL": (21, 21),
            }

            level_upper = level.upper()
            severity_number, default_num = severity_map.get(level_upper, (9, 9))

            # Convert attributes to Map(String, String) format
            attrs_map = {str(k): str(v) for k, v in attributes.items()}

            # Detect if message is JSON
            body_type = "STRING"
            try:
                json.loads(message)
                body_type = "JSON"
            except (json.JSONDecodeError, TypeError):
                pass

            # Build log row matching ClickHouse schema
            log_row = {
                "log_id": log_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp_ns": timestamp_ns,
                "observed_timestamp": observed_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "observed_timestamp_ns": observed_timestamp_ns,
                "severity_text": level_upper,
                "severity_number": severity_number,
                "body": message,
                "body_type": body_type,
                "project_name": resource_attributes.get("project.name", ""),
                "project_version": resource_attributes.get("project.version", ""),
                "service_name": resource_attributes.get("service.name", "unknown"),
                "service_namespace": resource_attributes.get("service.namespace", ""),
                "service_instance_id": resource_attributes.get("service.instance.id", ""),
                "environment": resource_attributes.get("deployment.environment", "production"),
                "hostname": resource_attributes.get("host.name", ""),
                "attributes": attrs_map,
                "user_id": attributes.get("user.id", ""),
                "session_id": attributes.get("session.id", ""),
                "os_type": resource_attributes.get("os.type", ""),
                "os_version": resource_attributes.get("os.version", ""),
                "runtime_name": resource_attributes.get("process.runtime.name", ""),
                "runtime_version": resource_attributes.get("process.runtime.version", ""),
                "cloud_provider": resource_attributes.get("cloud.provider", ""),
                "cloud_region": resource_attributes.get("cloud.region", ""),
                "cloud_availability_zone": resource_attributes.get("cloud.availability_zone", ""),
                "instrumentation_library_name": resource_attributes.get("telemetry.sdk.name", ""),
                "instrumentation_library_version": resource_attributes.get("telemetry.sdk.version", ""),
                "schema_url": "",
                "exception_type": attributes.get("exception.type", ""),
                "exception_message": attributes.get("exception.message", ""),
                "exception_stacktrace": attributes.get("exception.stacktrace", ""),
                "is_exception": 1 if "exception.type" in attributes else 0,
            }

            # Add to batch
            self._log_batch.append(log_row)

            # Auto-flush if batch size reached
            if len(self._log_batch) >= self.batch_size:
                self.flush()

            return True

        except Exception as e:
            logger.error(f"Error adding log to batch: {e}", exc_info=True)
            return False
