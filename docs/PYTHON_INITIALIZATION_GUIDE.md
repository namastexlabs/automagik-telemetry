# Python Initialization Guide

## Two Initialization Styles

Python SDK supports **TWO initialization styles** - choose based on your needs.

## Quick Comparison

| Feature | Direct Parameters (Simple) | TelemetryConfig (Advanced) |
|---------|---------------------------|----------------------------|
| **When to Use** | Quick start, prototyping, simple projects | Production apps, batching/compression, ClickHouse backend |
| **Available Parameters** | 5 basic parameters only | ALL configuration options (20+ parameters) |
| **Setup Complexity** | ✅ Minimal (2 lines) | ⚙️ More configuration (explicit config object) |
| **Performance Features** | ❌ No batching<br>❌ No compression control<br>❌ No retry tuning | ✅ Batching<br>✅ Compression<br>✅ Retry configuration |
| **Backend Support** | ⚠️ OTLP only | ✅ OTLP or ClickHouse |

## Available Parameters by Style

### Direct Parameters (Limited)

Only these **5 parameters** are available:

- `project_name` (required)
- `version` (required)
- `endpoint` (optional)
- `organization` (optional)
- `timeout` (optional)

### TelemetryConfig (Complete)

ALL parameters available:

**Basic Configuration:**
- `project_name` (required)
- `version` (required)
- `endpoint` (optional)
- `organization` (optional, default: "namastex")
- `timeout` (optional, default: 5 seconds)

**Performance Features:** ⚡
- `batch_size` (default: 100) - Number of events to batch before sending
- `flush_interval` (default: 5.0) - Auto-flush interval in seconds
- `compression_enabled` (default: True) - Enable gzip compression
- `compression_threshold` (default: 1024) - Minimum size for compression in bytes

**Reliability:** 🔄
- `max_retries` (default: 3) - Maximum retry attempts
- `retry_backoff_base` (default: 1.0) - Base backoff time in seconds

**Backend Selection:** 🗄️
- `backend` (default: "otlp") - Backend type: "otlp" or "clickhouse"
- `metrics_endpoint` (optional) - Custom metrics endpoint
- `logs_endpoint` (optional) - Custom logs endpoint

**ClickHouse Backend:** 📊
- `clickhouse_endpoint` (default: "http://localhost:8123")
- `clickhouse_database` (default: "telemetry")
- `clickhouse_table` (default: "traces")
- `clickhouse_username` (default: "default")
- `clickhouse_password` (default: "")

## Style 1: Direct Parameters

**Best for:**
- ✅ Quick start and prototyping
- ✅ Simple projects with low telemetry volume
- ✅ Getting familiar with the SDK
- ✅ Development and testing

**Example:**
```python
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig

# Simple initialization - just the essentials
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    endpoint="https://custom-collector.com",  # Optional
    organization="my-org",  # Optional (default: "namastex")
    timeout=10  # Optional (default: 5 seconds)
)
client = AutomagikTelemetry(config=config)

# Use client normally
client.track_event("app.started", {"env": "production"})
client.track_metric("requests", 1)
```

**Limitations:**
- ⚠️ No batching (sends immediately, may be slower for high volume)
- ⚠️ No compression control (uses defaults)
- ⚠️ No retry configuration
- ⚠️ Cannot use ClickHouse backend
- ⚠️ Cannot customize metrics/logs endpoints separately

## Style 2: TelemetryConfig

**Best for:**
- ✅ Production applications
- ✅ High-volume telemetry (100+ events/second)
- ✅ Self-hosted ClickHouse deployments
- ✅ Performance tuning and optimization
- ✅ Advanced reliability requirements

**Example - Basic Advanced Setup:**
```python
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig

config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",

    # Performance optimization
    batch_size=100,  # Batch 100 events before sending
    flush_interval=5.0,  # Auto-flush every 5 seconds
    compression_enabled=True,  # Gzip compression
    compression_threshold=1024  # Compress payloads > 1KB
)

client = AutomagikTelemetry(config=config)
```

**Example - ClickHouse Backend:**
```python
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig

config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",

    # Use ClickHouse backend instead of OTLP
    backend="clickhouse",
    clickhouse_endpoint="http://localhost:8123",
    clickhouse_database="telemetry",
    clickhouse_username="default",
    clickhouse_password="",

    # Performance tuning
    batch_size=100,
    compression_enabled=True
)

client = AutomagikTelemetry(config=config)
```

**Example - Full Configuration:**
```python
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig

config = TelemetryConfig(
    # Required
    project_name="my-app",
    version="1.0.0",

    # Basic config
    endpoint="https://telemetry.example.com/v1/traces",
    organization="my-org",
    timeout=10,

    # Performance
    batch_size=100,
    flush_interval=5.0,
    compression_enabled=True,
    compression_threshold=1024,

    # Reliability
    max_retries=3,
    retry_backoff_base=1.0,

    # Custom endpoints
    metrics_endpoint="https://telemetry.example.com/v1/metrics",
    logs_endpoint="https://telemetry.example.com/v1/logs"
)

client = AutomagikTelemetry(config=config)
```

## Decision Tree

```
┌─────────────────────────────────────┐
│ Do you need ClickHouse backend?     │
└────────────┬────────────────────────┘
             │
    YES ─────┼────> Use TelemetryConfig
             │
             NO
             │
             ▼
┌─────────────────────────────────────┐
│ Do you need batching or compression?│
└────────────┬────────────────────────┘
             │
    YES ─────┼────> Use TelemetryConfig
             │
             NO
             │
             ▼
┌─────────────────────────────────────┐
│ High-volume app (100+ events/sec)?  │
└────────────┬────────────────────────┘
             │
    YES ─────┼────> Use TelemetryConfig
             │
             NO
             │
             ▼
┌─────────────────────────────────────┐
│ Production deployment?               │
└────────────┬────────────────────────┘
             │
    YES ─────┼────> Consider TelemetryConfig
             │
             NO
             │
             ▼
┌─────────────────────────────────────┐
│ Just getting started or prototyping?│
└────────────┬────────────────────────┘
             │
    YES ─────┼────> Use Direct Parameters
             │
             ▼
         Perfect!
```

## Migration Path

### Start Simple, Upgrade When Needed

**Stage 1: Quick Prototype**
```python
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig

# Simple start - perfect for prototyping
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0"
)
client = AutomagikTelemetry(config=config)
```

**Stage 2: Need Better Performance**
```python
# Upgrade to batching when volume increases
from automagik_telemetry import TelemetryConfig

config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    batch_size=100,  # Now you can batch events!
    compression_enabled=True  # And compress large payloads!
)
client = AutomagikTelemetry(config=config)
```

**Stage 3: Self-Hosting with ClickHouse**
```python
# Switch to ClickHouse for self-hosted deployment
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    backend="clickhouse",  # Direct database writes
    clickhouse_endpoint="http://localhost:8123",
    clickhouse_database="telemetry",
    batch_size=100,
    compression_enabled=True
)
client = AutomagikTelemetry(config=config)
```

**Stage 4: Production-Ready with Full Tuning**
```python
# Fine-tune everything for production
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",

    # Backend
    backend="clickhouse",
    clickhouse_endpoint="http://clickhouse-prod:8123",
    clickhouse_database="telemetry_prod",
    clickhouse_username="telemetry_user",
    clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD"),

    # Performance
    batch_size=200,  # Larger batches for high volume
    flush_interval=3.0,  # More frequent flushes
    compression_enabled=True,
    compression_threshold=512,  # Compress smaller payloads

    # Reliability
    max_retries=5,  # More retries for critical data
    retry_backoff_base=2.0,  # Longer backoff
    timeout=15  # Longer timeout for reliability
)
client = AutomagikTelemetry(config=config)
```

## Common Patterns

### Pattern 1: Environment-Based Configuration

```python
import os
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig

# Different config for dev vs prod
if os.getenv("ENVIRONMENT") == "production":
    config = TelemetryConfig(
        project_name="my-app",
        version="1.0.0",
        backend="clickhouse",
        clickhouse_endpoint=os.getenv("CLICKHOUSE_ENDPOINT"),
        batch_size=100,
        compression_enabled=True
    )
    client = AutomagikTelemetry(config=config)
else:
    # Simple config for development
    dev_config = TelemetryConfig(
        project_name="my-app",
        version="1.0.0"
    )
    client = AutomagikTelemetry(config=dev_config)
```

### Pattern 2: Feature Flags

```python
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig

# Start with direct params, add features via config
ENABLE_BATCHING = os.getenv("TELEMETRY_BATCHING", "false") == "true"

if ENABLE_BATCHING:
    config = TelemetryConfig(
        project_name="my-app",
        version="1.0.0",
        batch_size=100
    )
    client = AutomagikTelemetry(config=config)
else:
    simple_config = TelemetryConfig(
        project_name="my-app",
        version="1.0.0"
    )
    client = AutomagikTelemetry(config=simple_config)
```

## Summary

| Aspect | Direct Parameters | TelemetryConfig |
|--------|------------------|-----------------|
| **Ease of Use** | ⭐⭐⭐⭐⭐ Very simple | ⭐⭐⭐ Requires more setup |
| **Flexibility** | ⭐⭐ Limited (5 params) | ⭐⭐⭐⭐⭐ Complete control |
| **Performance** | ⭐⭐ Basic (immediate send) | ⭐⭐⭐⭐⭐ Optimized (batching, compression) |
| **Backend Support** | ⭐⭐⭐ OTLP only | ⭐⭐⭐⭐⭐ OTLP + ClickHouse |
| **Production Ready** | ⭐⭐⭐ Good for small apps | ⭐⭐⭐⭐⭐ Production-optimized |

**Key Takeaways:**

1. **Direct Parameters** = Quick start, limited features
2. **TelemetryConfig** = Full control, all features
3. Start simple, migrate when you need advanced features
4. TelemetryConfig is REQUIRED for:
   - Batching events
   - Custom compression settings
   - ClickHouse backend
   - Retry configuration
   - Separate metrics/logs endpoints

**When in doubt:** Start with direct parameters, upgrade to TelemetryConfig when you need better performance or advanced features.
