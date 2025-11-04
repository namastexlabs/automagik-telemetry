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
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import TelemetryBackend

logger = logging.getLogger(__name__)


class ClickHouseBackend(TelemetryBackend):
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
        retry_backoff_base: float = 1.0,
        verbose: bool = False,
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
            retry_backoff_base: Base backoff time in seconds for exponential backoff (default: 1.0)
            verbose: Enable verbose logging (default: False)
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
        self.retry_backoff_base = retry_backoff_base
        self.verbose = verbose

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
        timestamp = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=UTC)

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
            "cloud_provider": resource_attrs.get("cloud.provider", ""),
            "cloud_region": resource_attrs.get("cloud.region", ""),
            "cloud_availability_zone": resource_attrs.get("cloud.availability_zone", ""),
            "instrumentation_library_name": resource_attrs.get("telemetry.sdk.name", ""),
            "instrumentation_library_version": resource_attrs.get("telemetry.sdk.version", ""),
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
            auth_string = f"{self.username}:{self.password}".encode()
            import base64

            auth_header = b"Basic " + base64.b64encode(auth_string)
        else:
            auth_header = None

        # Retry logic with exponential backoff
        last_exception = None
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
                        if self.verbose:
                            print(f"Inserted {len(rows)} rows to ClickHouse table {table_name} successfully")
                        logger.debug(
                            f"Inserted {len(rows)} rows to ClickHouse table {table_name} successfully"
                        )
                        return True
                    elif response.status >= 500:
                        # Server error - retry
                        last_exception = Exception(
                            f"ClickHouse returned status {response.status}: {response.read().decode('utf-8')}"
                        )
                    else:
                        # Client error - don't retry
                        if self.verbose:
                            print(f"ClickHouse returned status {response.status}")
                        logger.warning(
                            f"ClickHouse returned status {response.status}: {response.read().decode('utf-8')}"
                        )
                        return False

            except (HTTPError, URLError, TimeoutError, Exception) as e:
                last_exception = e
                # Check if we should retry
                if isinstance(e, HTTPError) and e.code < 500:
                    # Client error - don't retry
                    if self.verbose:
                        print(f"Failed to insert to ClickHouse: {e}")
                    logger.error(f"HTTP error inserting to ClickHouse: {e}")
                    return False

                if self.verbose:
                    print(f"Error inserting to ClickHouse (attempt {attempt + 1}/{self.max_retries}): {e}")
                logger.debug(f"Error inserting to ClickHouse (attempt {attempt + 1}/{self.max_retries}): {e}")

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                backoff_time = self.retry_backoff_base * (2**attempt)
                time.sleep(backoff_time)

        # All retries exhausted
        if last_exception:
            if self.verbose:
                print(f"Failed to insert to ClickHouse after {self.max_retries} retries: {last_exception}")
            logger.debug(f"Failed to insert to ClickHouse after {self.max_retries} retries: {last_exception}")
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
        payload: dict[str, Any] | str | None = None,
        value: float | None = None,
        metric_type: str = "gauge",
        unit: str = "",
        attributes: dict[str, Any] | None = None,
        resource_attributes: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        Send a single metric to ClickHouse.

        This method supports two calling conventions:
        1. Dict payload (matches base class interface):
           send_metric(payload={'metric_name': '...', 'value': 1.0, ...})
        2. Keyword arguments (backward compatible):
           send_metric(metric_name='...', value=1.0, ...)

        Args:
            payload: Dict containing metric data (new interface, matches base class).
                     If provided as dict, takes precedence over keyword arguments.
                     If provided as str, treated as metric_name (backward compatible).
                     Expected dict keys: metric_name, value, metric_type, unit,
                                        attributes, resource_attributes, timestamp
            value: Numeric value of the metric (for backward compatibility)
            metric_type: Type of metric (gauge, counter, histogram, summary) - default: gauge
            unit: Unit of measurement (ms, bytes, requests, etc.)
            attributes: Metric-specific attributes/labels
            resource_attributes: Service/application resource attributes
            timestamp: Timestamp for the metric (default: now)
            **kwargs: Additional keyword arguments (supports metric_name for backward compatibility)

        Returns:
            True if added to batch successfully
        """
        try:
            # Support both dict payload (new interface) and keyword args (backward compatible)
            metric_name: str
            metric_value: float

            if isinstance(payload, dict):
                # New interface: extract from payload dict
                metric_name = payload.get("metric_name", "")
                metric_value = payload.get("value", 0.0)
                metric_type = payload.get("metric_type", "gauge")
                unit = payload.get("unit", "")
                attributes = payload.get("attributes")
                resource_attributes = payload.get("resource_attributes")
                timestamp = payload.get("timestamp")
            elif isinstance(payload, str):
                # Backward compatible: payload is metric_name
                metric_name = payload
                metric_value = value if value is not None else 0.0
            else:
                # Backward compatible: check kwargs for metric_name
                metric_name = kwargs.get("metric_name", "")
                metric_value = value if value is not None else 0.0

            # Validate required parameters
            if not metric_name:
                logger.error("send_metric requires metric_name")
                return False
            if value is None and not isinstance(payload, dict):
                logger.error("send_metric requires value")
                return False

            # Default values
            if attributes is None:
                attributes = {}
            if resource_attributes is None:
                resource_attributes = {}
            if timestamp is None:
                timestamp = datetime.now(UTC)

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
            is_int = isinstance(metric_value, int) and not isinstance(metric_value, bool)
            value_int = int(metric_value) if is_int else 0
            value_double = 0.0 if is_int else float(metric_value)

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
                "instrumentation_library_version": resource_attributes.get(
                    "telemetry.sdk.version", ""
                ),
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
        payload: dict[str, Any] | str | None = None,
        level: str = "INFO",
        attributes: dict[str, Any] | None = None,
        resource_attributes: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
        trace_id: str = "",
        span_id: str = "",
        **kwargs: Any,
    ) -> bool:
        """
        Send a single log entry to ClickHouse.

        This method supports two calling conventions:
        1. Dict payload (matches base class interface):
           send_log(payload={'message': '...', 'level': 'INFO', ...})
        2. Keyword arguments (backward compatible):
           send_log(message='...', level='INFO', ...)

        Args:
            payload: Dict containing log data (new interface, matches base class).
                     If provided as dict, takes precedence over keyword arguments.
                     If provided as str, treated as message (backward compatible).
                     Expected dict keys: message, level, attributes, resource_attributes,
                                        timestamp, trace_id, span_id
            level: Severity level (TRACE, DEBUG, INFO, WARN, ERROR, FATAL)
            attributes: Log-specific attributes/context
            resource_attributes: Service/application resource attributes
            timestamp: Timestamp for the log (default: now)
            trace_id: Optional trace ID for correlation
            span_id: Optional span ID for correlation
            **kwargs: Additional keyword arguments (supports message for backward compatibility)

        Returns:
            True if added to batch successfully
        """
        try:
            # Support both dict payload (new interface) and keyword args (backward compatible)
            message: str

            if isinstance(payload, dict):
                # New interface: extract from payload dict
                message = payload.get("message", "")
                level = payload.get("level", "INFO")
                attributes = payload.get("attributes")
                resource_attributes = payload.get("resource_attributes")
                timestamp = payload.get("timestamp")
                trace_id = payload.get("trace_id", "")
                span_id = payload.get("span_id", "")
            elif isinstance(payload, str):
                # Backward compatible: payload is message
                message = payload
            else:
                # Backward compatible: check kwargs for message
                message = kwargs.get("message", "")

            # Note: Empty messages are allowed (unlike metrics which require values)

            # Default values
            if attributes is None:
                attributes = {}
            if resource_attributes is None:
                resource_attributes = {}
            if timestamp is None:
                timestamp = datetime.now(UTC)

            # Extract trace_id and span_id from attributes if not provided
            # This allows logs to be correlated with traces
            if not trace_id and "trace_id" in attributes:
                trace_id = str(attributes.get("trace_id", ""))
            if not span_id and "span_id" in attributes:
                span_id = str(attributes.get("span_id", ""))

            # Generate unique log_id
            log_id = str(uuid.uuid4())

            # Calculate timestamps
            timestamp_ns = int(timestamp.timestamp() * 1_000_000_000)
            observed_timestamp = datetime.now(UTC)
            observed_timestamp_ns = int(observed_timestamp.timestamp() * 1_000_000_000)

            # Map severity levels to OTLP standard numbers
            severity_map = {
                "TRACE": (1, 1),
                "DEBUG": (5, 5),
                "INFO": (9, 9),
                "WARN": (13, 13),
                "ERROR": (17, 17),
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
                "instrumentation_library_version": resource_attributes.get(
                    "telemetry.sdk.version", ""
                ),
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
