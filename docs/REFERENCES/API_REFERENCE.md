# API Reference

> **🚀 Complete API documentation** for AutomagikTelemetry SDK with side-by-side Python/TypeScript examples.

---

## 📖 Table of Contents

- [Class: AutomagikTelemetry](#class-automagiktelemetry)
- [Configuration](#configuration)
- [Enums](#enums)
- [Public Methods](#public-methods)
- [Usage Patterns](#usage-patterns)

---

## Class: AutomagikTelemetry

Privacy-first telemetry client for tracking events, metrics, logs, and errors in your application.

### Constructor

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
from automagik_telemetry import (
    AutomagikTelemetry,
    TelemetryConfig
)

# Simple initialization
telemetry = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Advanced initialization
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    backend="otlp",
    batch_size=100,
    timeout=10
)
telemetry = AutomagikTelemetry(config=config)
```

</td>
<td>

```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

// Simple initialization
const telemetry = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Advanced initialization
const telemetry = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    backend: 'otlp',
    batchSize: 100,
    timeout: 10000
});
```

</td>
</tr>
</table>

#### Constructor Parameters

| Parameter (Python) | Parameter (TypeScript) | Type | Required | Default | Description |
|-------------------|------------------------|------|----------|---------|-------------|
| `project_name` | `projectName` | `string` | ✅ Yes | - | Name of your project |
| `version` | `version` | `string` | ✅ Yes | - | Project version |
| `backend` | `backend` | `string` | No | `"otlp"` | Backend type: `"otlp"` or `"clickhouse"` |
| `endpoint` | `endpoint` | `string` | No | `https://telemetry.namastex.ai/v1/traces` | Custom OTLP endpoint |
| `organization` | `organization` | `string` | No | `"namastex"` | Organization name |
| `timeout` | `timeout` | `int` | No | Python: `5` (sec)<br>TypeScript: `5000` (ms) | HTTP timeout |
| `config` | - | `TelemetryConfig` | No | - | Advanced config object (Python only) |

---

## Configuration

### TelemetryConfig Class

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
from automagik_telemetry import TelemetryConfig

config = TelemetryConfig(
    # Required
    project_name="my-app",
    version="1.0.0",

    # Backend selection
    backend="otlp",  # or "clickhouse"

    # OTLP configuration
    endpoint="https://custom.example.com/v1/traces",
    metrics_endpoint="https://custom.example.com/v1/metrics",
    logs_endpoint="https://custom.example.com/v1/logs",

    # ClickHouse configuration
    clickhouse_endpoint="http://localhost:8123",
    clickhouse_database="telemetry",
    clickhouse_table="traces",
    clickhouse_username="default",
    clickhouse_password="",

    # Performance tuning
    timeout=10,  # seconds
    batch_size=100,
    flush_interval=5.0,  # seconds

    # Compression
    compression_enabled=True,
    compression_threshold=1024,  # bytes

    # Retry logic
    max_retries=3,
    retry_backoff_base=1.0  # seconds
)
```

</td>
<td>

```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const config = {
    // Required
    projectName: 'my-app',
    version: '1.0.0',

    // Backend selection
    backend: 'otlp',  // or 'clickhouse'

    // OTLP configuration
    endpoint: 'https://custom.example.com/v1/traces',
    metricsEndpoint: 'https://custom.example.com/v1/metrics',
    logsEndpoint: 'https://custom.example.com/v1/logs',

    // ClickHouse configuration
    clickhouseEndpoint: 'http://localhost:8123',
    clickhouseDatabase: 'telemetry',
    clickhouseTable: 'traces',
    clickhouseUsername: 'default',
    clickhousePassword: '',

    // Performance tuning
    timeout: 10000,  // milliseconds
    batchSize: 100,
    flushInterval: 5000,  // milliseconds

    // Compression
    compressionEnabled: true,
    compressionThreshold: 1024,  // bytes

    // Retry logic
    maxRetries: 3,
    retryBackoffBase: 1000  // milliseconds
};

const telemetry = new AutomagikTelemetry(config);
```

</td>
</tr>
</table>

### Configuration Parameters

| Parameter (Python) | Parameter (TypeScript) | Type | Default | Description |
|-------------------|------------------------|------|---------|-------------|
| **Backend Selection** |
| `backend` | `backend` | `string` | `"otlp"` | Backend type: `"otlp"` or `"clickhouse"` |
| **OTLP Backend** |
| `endpoint` | `endpoint` | `string` | `https://telemetry.namastex.ai/v1/traces` | Main traces endpoint |
| `metrics_endpoint` | `metricsEndpoint` | `string` | Auto-derived | Metrics endpoint |
| `logs_endpoint` | `logsEndpoint` | `string` | Auto-derived | Logs endpoint |
| **ClickHouse Backend** |
| `clickhouse_endpoint` | `clickhouseEndpoint` | `string` | `http://localhost:8123` | ClickHouse HTTP endpoint |
| `clickhouse_database` | `clickhouseDatabase` | `string` | `"telemetry"` | Database name |
| `clickhouse_table` | `clickhouseTable` | `string` | `"traces"` | Table name |
| `clickhouse_username` | `clickhouseUsername` | `string` | `"default"` | Username |
| `clickhouse_password` | `clickhousePassword` | `string` | `""` | Password |
| **Performance** |
| `timeout` | `timeout` | `int` | Python: `5` (sec)<br>TypeScript: `5000` (ms) | HTTP timeout |
| `batch_size` | `batchSize` | `int` | Python: `1`<br>TypeScript: `100` | Events per batch |
| `flush_interval` | `flushInterval` | `float`/`int` | Python: `5.0` (sec)<br>TypeScript: `5000` (ms) | Auto-flush interval |
| **Compression** |
| `compression_enabled` | `compressionEnabled` | `bool` | `true` | Enable gzip compression |
| `compression_threshold` | `compressionThreshold` | `int` | `1024` | Min size for compression (bytes) |
| **Retry Logic** |
| `max_retries` | `maxRetries` | `int` | `3` | Max retry attempts |
| `retry_backoff_base` | `retryBackoffBase` | `float`/`int` | Python: `1.0` (sec)<br>TypeScript: `1000` (ms) | Backoff base time |

---

## Enums

### MetricType

Used to specify the type of metric being tracked.

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
from automagik_telemetry import MetricType

# Available values
MetricType.GAUGE      # Point-in-time value
MetricType.COUNTER    # Monotonic counter
MetricType.HISTOGRAM  # Distribution of values
```

</td>
<td>

```typescript
import { MetricType } from '@automagik/telemetry';

// Available values
MetricType.GAUGE      // Point-in-time value
MetricType.COUNTER    // Monotonic counter
MetricType.HISTOGRAM  // Distribution of values
```

</td>
</tr>
</table>

**Metric Type Descriptions:**

| Type | Use Case | Example |
|------|----------|---------|
| **GAUGE** | Current value that can go up or down | CPU usage, memory usage, queue size |
| **COUNTER** | Monotonically increasing value | Total requests, total errors, total sales |
| **HISTOGRAM** | Distribution of measurements | Response times, payload sizes, latencies |

---

### LogSeverity

Used to specify the severity level of log messages.

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
from automagik_telemetry import LogSeverity

# Available values (OTLP standard)
LogSeverity.TRACE  # 1  - Finest detail
LogSeverity.DEBUG  # 5  - Debug info
LogSeverity.INFO   # 9  - Informational
LogSeverity.WARN   # 13 - Warning
LogSeverity.ERROR  # 17 - Error occurred
LogSeverity.FATAL  # 21 - Fatal error
```

</td>
<td>

```typescript
import { LogSeverity } from '@automagik/telemetry';

// Available values (OTLP standard)
LogSeverity.TRACE  // 1  - Finest detail
LogSeverity.DEBUG  // 5  - Debug info
LogSeverity.INFO   // 9  - Informational
LogSeverity.WARN   // 13 - Warning
LogSeverity.ERROR  // 17 - Error occurred
LogSeverity.FATAL  // 21 - Fatal error
```

</td>
</tr>
</table>

---

## Public Methods

### track_event() / trackEvent()

Track a telemetry event (span/trace).

**Signature:**

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
def track_event(
    self,
    event_name: str,
    attributes: dict[str, Any] | None = None
) -> None
```

</td>
<td>

```typescript
trackEvent(
    event_name: string,
    attributes?: Record<string, any>
): void
```

</td>
</tr>
</table>

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `event_name` | `string` | ✅ Yes | Event name (e.g., `"user.login"`, `"api.request"`) |
| `attributes` | `dict`/`Record` | No | Event attributes (key-value pairs) |

**Examples:**

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
from automagik_telemetry import AutomagikTelemetry

telemetry = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Simple event
telemetry.track_event("user.login")

# Event with attributes
telemetry.track_event("api.request", {
    "endpoint": "/v1/users",
    "method": "GET",
    "status": 200,
    "duration_ms": 45.2
})

# Feature usage
telemetry.track_event("feature.used", {
    "feature_name": "export_data",
    "format": "csv",
    "row_count": 1500
})
```

</td>
<td>

```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const telemetry = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Simple event
telemetry.trackEvent('user.login');

// Event with attributes
telemetry.trackEvent('api.request', {
    endpoint: '/v1/users',
    method: 'GET',
    status: 200,
    duration_ms: 45.2
});

// Feature usage
telemetry.trackEvent('feature.used', {
    feature_name: 'export_data',
    format: 'csv',
    row_count: 1500
});
```

</td>
</tr>
</table>

---

### track_metric() / trackMetric()

Track a numeric metric with optional metric type.

**Signature:**

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
def track_metric(
    self,
    metric_name: str,
    value: float,
    metric_type: MetricType | str = MetricType.GAUGE,
    attributes: dict[str, Any] | None = None
) -> None
```

</td>
<td>

```typescript
trackMetric(
    metric_name: string,
    value: number,
    metric_type?: MetricType | string,
    attributes?: Record<string, any>
): void
```

</td>
</tr>
</table>

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `metric_name` | `string` | ✅ Yes | - | Metric name (e.g., `"cpu.usage"`) |
| `value` | `float`/`number` | ✅ Yes | - | Metric value |
| `metric_type` | `MetricType` | No | `MetricType.GAUGE` | Type of metric |
| `attributes` | `dict`/`Record` | No | `{}` | Additional attributes |

**Examples:**

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
from automagik_telemetry import (
    AutomagikTelemetry,
    MetricType
)

telemetry = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Gauge metric (default)
telemetry.track_metric("cpu.usage", 75.5)

# Counter metric
telemetry.track_metric(
    "api.requests.total",
    1,
    MetricType.COUNTER,
    {"endpoint": "/v1/users"}
)

# Histogram metric
telemetry.track_metric(
    "api.latency_ms",
    123.45,
    MetricType.HISTOGRAM,
    {
        "endpoint": "/v1/users",
        "method": "GET"
    }
)

# Memory usage gauge
telemetry.track_metric(
    "memory.used_mb",
    512.0,
    attributes={"process": "worker"}
)
```

</td>
<td>

```typescript
import {
    AutomagikTelemetry,
    MetricType
} from '@automagik/telemetry';

const telemetry = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Gauge metric (default)
telemetry.trackMetric('cpu.usage', 75.5);

// Counter metric
telemetry.trackMetric(
    'api.requests.total',
    1,
    MetricType.COUNTER,
    { endpoint: '/v1/users' }
);

// Histogram metric
telemetry.trackMetric(
    'api.latency_ms',
    123.45,
    MetricType.HISTOGRAM,
    {
        endpoint: '/v1/users',
        method: 'GET'
    }
);

// Memory usage gauge
telemetry.trackMetric(
    'memory.used_mb',
    512.0,
    undefined,
    { process: 'worker' }
);
```

</td>
</tr>
</table>

---

### track_log() / trackLog()

Track a log message with severity level.

**Signature:**

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
def track_log(
    self,
    message: str,
    severity: LogSeverity | str = LogSeverity.INFO,
    attributes: dict[str, Any] | None = None
) -> None
```

</td>
<td>

```typescript
trackLog(
    message: string,
    severity?: LogSeverity | string,
    attributes?: Record<string, any>
): void
```

</td>
</tr>
</table>

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `message` | `string` | ✅ Yes | - | Log message (max 1000 chars) |
| `severity` | `LogSeverity` | No | `LogSeverity.INFO` | Log severity level |
| `attributes` | `dict`/`Record` | No | `{}` | Additional attributes |

**Examples:**

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
from automagik_telemetry import (
    AutomagikTelemetry,
    LogSeverity
)

telemetry = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Info log (default)
telemetry.track_log("Application started")

# Debug log
telemetry.track_log(
    "Database connection established",
    LogSeverity.DEBUG,
    {"host": "db.example.com"}
)

# Warning log
telemetry.track_log(
    "API rate limit approaching",
    LogSeverity.WARN,
    {
        "current": 450,
        "limit": 500
    }
)

# Error log
telemetry.track_log(
    "Payment processing failed",
    LogSeverity.ERROR,
    {
        "error_code": "PAY-1001",
        "transaction_id": "tx_abc123"
    }
)
```

</td>
<td>

```typescript
import {
    AutomagikTelemetry,
    LogSeverity
} from '@automagik/telemetry';

const telemetry = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Info log (default)
telemetry.trackLog('Application started');

// Debug log
telemetry.trackLog(
    'Database connection established',
    LogSeverity.DEBUG,
    { host: 'db.example.com' }
);

// Warning log
telemetry.trackLog(
    'API rate limit approaching',
    LogSeverity.WARN,
    {
        current: 450,
        limit: 500
    }
);

// Error log
telemetry.trackLog(
    'Payment processing failed',
    LogSeverity.ERROR,
    {
        error_code: 'PAY-1001',
        transaction_id: 'tx_abc123'
    }
);
```

</td>
</tr>
</table>

---

### track_error() / trackError()

Track an error with context information.

**Signature:**

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
def track_error(
    self,
    error: Exception,
    context: dict[str, Any] | None = None
) -> None
```

</td>
<td>

```typescript
trackError(
    error: Error,
    context?: Record<string, any>
): void
```

</td>
</tr>
</table>

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `error` | `Exception`/`Error` | ✅ Yes | The exception/error that occurred |
| `context` | `dict`/`Record` | No | Additional context about the error |

**Examples:**

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
from automagik_telemetry import AutomagikTelemetry

telemetry = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Simple error tracking
try:
    risky_operation()
except Exception as e:
    telemetry.track_error(e)

# Error with context
try:
    process_payment(order_id="order_123")
except PaymentError as e:
    telemetry.track_error(e, {
        "error_code": "PAY-1001",
        "order_id": "order_123",
        "amount": 99.99,
        "currency": "USD",
        "recoverable": False
    })

# API error tracking
try:
    response = api_call()
except requests.HTTPError as e:
    telemetry.track_error(e, {
        "endpoint": "/v1/users",
        "status_code": e.response.status_code,
        "method": "POST"
    })
```

</td>
<td>

```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const telemetry = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Simple error tracking
try {
    riskyOperation();
} catch (error) {
    telemetry.trackError(error as Error);
}

// Error with context
try {
    processPayment('order_123');
} catch (error) {
    telemetry.trackError(error as Error, {
        error_code: 'PAY-1001',
        order_id: 'order_123',
        amount: 99.99,
        currency: 'USD',
        recoverable: false
    });
}

// API error tracking
try {
    const response = await apiCall();
} catch (error) {
    telemetry.trackError(error as Error, {
        endpoint: '/v1/users',
        status_code: (error as any).status,
        method: 'POST'
    });
}
```

</td>
</tr>
</table>

---

### flush()

Manually flush all queued events to the telemetry backend.

**Signature:**

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
def flush(self) -> None
```

</td>
<td>

```typescript
flush(): Promise<void>
```

</td>
</tr>
</table>

**Examples:**

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
from automagik_telemetry import AutomagikTelemetry

telemetry = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Track events
telemetry.track_event("app.startup")
telemetry.track_metric("cpu.usage", 45.2)

# Flush before shutdown
telemetry.flush()
```

</td>
<td>

```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const telemetry = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Track events
telemetry.trackEvent('app.startup');
telemetry.trackMetric('cpu.usage', 45.2);

// Flush before shutdown
await telemetry.flush();
```

</td>
</tr>
</table>

**💡 When to Use:**
- Before application shutdown
- At critical checkpoints
- When batch_size > 1 and you need immediate send
- After tracking important events that must be delivered

---

### Async Methods (Python Only)

Python SDK provides async versions of all tracking methods for use in async contexts.

**Available Methods:**
- `track_event_async()`
- `track_metric_async()`
- `track_log_async()`
- `track_error_async()`
- `flush_async()`

**Example:**

```python
import asyncio
from automagik_telemetry import (
    AutomagikTelemetry,
    MetricType,
    LogSeverity
)

telemetry = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

async def main():
    # Async event tracking
    await telemetry.track_event_async("user.login", {
        "user_id": "anonymous-123"
    })

    # Async metric tracking
    await telemetry.track_metric_async(
        "api.latency_ms",
        123.45,
        MetricType.HISTOGRAM
    )

    # Async log tracking
    await telemetry.track_log_async(
        "User authenticated successfully",
        LogSeverity.INFO
    )

    # Async error tracking
    try:
        raise ValueError("Test error")
    except Exception as e:
        await telemetry.track_error_async(e, {
            "context": "test"
        })

    # Async flush
    await telemetry.flush_async()

asyncio.run(main())
```

---

### Control Methods

#### enable() / disable()

Enable or disable telemetry at runtime.

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
# Enable telemetry
telemetry.enable()

# Disable telemetry
telemetry.disable()
```

</td>
<td>

```typescript
// Enable telemetry
telemetry.enable();

// Disable telemetry
telemetry.disable();
```

</td>
</tr>
</table>

---

#### is_enabled() / isEnabled()

Check if telemetry is currently enabled.

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
if telemetry.is_enabled():
    print("Telemetry is active")
else:
    print("Telemetry is disabled")
```

</td>
<td>

```typescript
if (telemetry.isEnabled()) {
    console.log('Telemetry is active');
} else {
    console.log('Telemetry is disabled');
}
```

</td>
</tr>
</table>

---

#### get_status() / getStatus()

Get comprehensive telemetry status information.

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
status = telemetry.get_status()

# Returns:
# {
#     "enabled": True,
#     "user_id": "uuid...",
#     "session_id": "uuid...",
#     "project_name": "my-app",
#     "project_version": "1.0.0",
#     "endpoint": "https://...",
#     "verbose": False,
#     "batch_size": 100,
#     "queue_sizes": {
#         "traces": 5,
#         "metrics": 2,
#         "logs": 0
#     }
# }
```

</td>
<td>

```typescript
const status = telemetry.getStatus();

// Returns:
// {
//     enabled: true,
//     userId: 'uuid...',
//     sessionId: 'uuid...',
//     projectName: 'my-app',
//     projectVersion: '1.0.0',
//     endpoint: 'https://...',
//     verbose: false,
//     batchSize: 100,
//     queueSize: 5
// }
```

</td>
</tr>
</table>

---

## Usage Patterns

### Performance Monitoring

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
import time
from automagik_telemetry import (
    AutomagikTelemetry,
    MetricType
)

telemetry = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Time an operation
start = time.time()
result = expensive_operation()
duration_ms = (time.time() - start) * 1000

# Track as histogram
telemetry.track_metric(
    "operation.duration_ms",
    duration_ms,
    MetricType.HISTOGRAM,
    {
        "operation": "data_processing",
        "success": True
    }
)
```

</td>
<td>

```typescript
import {
    AutomagikTelemetry,
    MetricType
} from '@automagik/telemetry';

const telemetry = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Time an operation
const start = performance.now();
const result = await expensiveOperation();
const duration_ms = performance.now() - start;

// Track as histogram
telemetry.trackMetric(
    'operation.duration_ms',
    duration_ms,
    MetricType.HISTOGRAM,
    {
        operation: 'data_processing',
        success: true
    }
);
```

</td>
</tr>
</table>

---

### Feature Flag Tracking

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
def use_feature(feature_name: str):
    # Feature logic here
    perform_feature_action()

    # Track usage
    telemetry.track_event("feature.used", {
        "feature_name": feature_name,
        "user_type": "premium",
        "platform": "web"
    })
```

</td>
<td>

```typescript
function useFeature(featureName: string): void {
    // Feature logic here
    performFeatureAction();

    // Track usage
    telemetry.trackEvent('feature.used', {
        feature_name: featureName,
        user_type: 'premium',
        platform: 'web'
    });
}
```

</td>
</tr>
</table>

---

### API Request Tracking

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
from automagik_telemetry import MetricType

@app.route("/api/users")
def get_users():
    start = time.time()

    try:
        users = fetch_users()
        duration = (time.time() - start) * 1000

        # Track success
        telemetry.track_event("api.request", {
            "endpoint": "/api/users",
            "method": "GET",
            "status": 200
        })

        # Track latency
        telemetry.track_metric(
            "api.latency_ms",
            duration,
            MetricType.HISTOGRAM,
            {"endpoint": "/api/users"}
        )

        return users

    except Exception as e:
        # Track error
        telemetry.track_error(e, {
            "endpoint": "/api/users",
            "method": "GET"
        })
        raise
```

</td>
<td>

```typescript
import { MetricType } from '@automagik/telemetry';

app.get('/api/users', async (req, res) => {
    const start = performance.now();

    try {
        const users = await fetchUsers();
        const duration = performance.now() - start;

        // Track success
        telemetry.trackEvent('api.request', {
            endpoint: '/api/users',
            method: 'GET',
            status: 200
        });

        // Track latency
        telemetry.trackMetric(
            'api.latency_ms',
            duration,
            MetricType.HISTOGRAM,
            { endpoint: '/api/users' }
        );

        res.json(users);

    } catch (error) {
        // Track error
        telemetry.trackError(error as Error, {
            endpoint: '/api/users',
            method: 'GET'
        });
        throw error;
    }
});
```

</td>
</tr>
</table>

---

### Graceful Shutdown

<table>
<tr>
<th width="50%">Python</th>
<th width="50%">TypeScript</th>
</tr>
<tr>
<td>

```python
import signal
import sys

def signal_handler(sig, frame):
    print("Shutting down gracefully...")

    # Track shutdown event
    telemetry.track_event("app.shutdown", {
        "signal": sig,
        "graceful": True
    })

    # Flush all queued events
    telemetry.flush()

    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
```

</td>
<td>

```typescript
process.on('SIGTERM', async () => {
    console.log('Shutting down gracefully...');

    // Track shutdown event
    telemetry.trackEvent('app.shutdown', {
        signal: 'SIGTERM',
        graceful: true
    });

    // Flush all queued events
    await telemetry.flush();

    process.exit(0);
});

process.on('SIGINT', async () => {
    await telemetry.flush();
    process.exit(0);
});
```

</td>
</tr>
</table>

---

## 📚 Related Documentation

- [Environment Variables](/home/cezar/automagik-telemetry/docs/REFERENCES/ENVIRONMENT_VARIABLES.md) - All environment variable options
- [Troubleshooting](/home/cezar/automagik-telemetry/docs/REFERENCES/TROUBLESHOOTING.md) - Common issues and solutions
- [Configuration Reference](/home/cezar/automagik-telemetry/docs/CONFIGURATION_REFERENCE.md) - Detailed configuration guide

---

**Built with ❤️ by [Namastex Labs](https://namastex.ai)**
