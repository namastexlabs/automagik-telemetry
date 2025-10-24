<p align="center">
  <img src=".github/assets/telemetry-logo.svg" alt="Automagik Telemetry Logo" width="400">
</p>
<h2 align="center">Privacy-First OpenTelemetry SDK for Modern Applications</h2>

<p align="center">
  <strong>🎯 Zero-Dependency, Opt-In Telemetry with Production-Ready OTLP Protocol</strong><br>
  Built for developers who value privacy, performance, and observability.<br>
  100% test coverage. Python & TypeScript. Production-ready.
</p>

<p align="center">
  <a href="https://github.com/namastexlabs/automagik-telemetry/actions/workflows/python-ci.yml"><img alt="Python CI" src="https://img.shields.io/github/actions/workflow/status/namastexlabs/automagik-telemetry/python-ci.yml?branch=main&style=flat-square&label=python%20ci" /></a>
  <a href="https://github.com/namastexlabs/automagik-telemetry/actions/workflows/typescript-ci.yml"><img alt="TypeScript CI" src="https://img.shields.io/github/actions/workflow/status/namastexlabs/automagik-telemetry/typescript-ci.yml?branch=main&style=flat-square&label=typescript%20ci" /></a>
  <a href="https://pypi.org/project/automagik-telemetry/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/automagik-telemetry?style=flat-square&color=00D9FF" /></a>
  <a href="https://www.npmjs.com/package/@automagik/telemetry"><img alt="npm version" src="https://img.shields.io/npm/v/@automagik/telemetry?style=flat-square&color=00D9FF" /></a>
  <a href="https://github.com/namastexlabs/automagik-telemetry/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/namastexlabs/automagik-telemetry?style=flat-square&color=00D9FF" /></a>
  <a href="https://discord.gg/xcW8c7fF3R"><img alt="Discord" src="https://img.shields.io/discord/1095114867012292758?style=flat-square&color=00D9FF&label=discord" /></a>
</p>

<p align="center">
  <a href="docs/INDEX.md">📚 Documentation</a> •
  <a href="docs/GETTING_STARTED.md">🚀 Quick Start</a> •
  <a href="docs/USER_GUIDES/CONFIGURATION.md">⚙️ Configuration</a> •
  <a href="docs/DEVELOPER_GUIDES/ARCHITECTURE.md">🏗️ Architecture</a> •
  <a href="docs/DEVELOPER_GUIDES/CONTRIBUTING.md">🤝 Contributing</a>
</p>

---

## 🚀 What is Automagik Telemetry?

**Automagik Telemetry** is a privacy-first, zero-dependency telemetry SDK built on OpenTelemetry Protocol (OTLP). It provides production-ready observability for Python and TypeScript applications without compromising user privacy or adding heavy dependencies.

### 🎭 Why We Built This

**The Problem with Traditional Telemetry:**
- Heavy dependencies that bloat your application
- Privacy-invasive defaults that collect everything
- Complex setup requiring infrastructure expertise
- Vendor lock-in with proprietary formats
- No easy way to disable in development

**The Automagik Solution:**
- **Zero dependencies** - Pure Python/TypeScript implementation
- **Opt-in by default** - Disabled in development, enabled in production
- **Privacy-first** - No PII, no tracking, just metrics
- **OTLP standard** - Works with any OpenTelemetry-compatible backend
- **100% test coverage** - Battle-tested and reliable

### ✅ What Makes This Different

**Other SDKs Force You to Choose:**
- ❌ Easy setup OR production features
- ❌ Privacy OR comprehensive telemetry
- ❌ Lightweight OR fully featured

**Automagik Telemetry Gives You Everything:**
- ✅ **Zero Dependencies** - No bloat, no conflicts
- ✅ **Privacy-First Design** - Opt-in, environment-aware, no PII
- ✅ **Standard Protocol** - OTLP over HTTP/JSON
- ✅ **Dual SDK Support** - Python & TypeScript with identical APIs
- ✅ **100% Test Coverage** - Every line tested, production-ready
- ✅ **Developer-Friendly** - Auto-disabled in dev, easy configuration

---

## 🌟 Key Features

### 📡 **Dual Backend Support**
**OTLP Backend (Default):** Industry-standard telemetry protocol over HTTP. Works with Prometheus, Grafana, Jaeger, and any OTLP-compatible backend.

**ClickHouse Backend (Self-Hosting):** Direct insertion to ClickHouse for self-hosted deployments. Bypasses middleware, simpler architecture, better performance for local development.

### 🔒 **Privacy-First by Design**
```python
# Automatically disabled in development
os.environ["ENVIRONMENT"] = "development"  # No telemetry sent

# Explicit opt-out anytime
os.environ["AUTOMAGIK_TELEMETRY_ENABLED"] = "false"

# No PII collected - only anonymous metrics
```

### ⚡ **Zero Dependencies**
Pure Python (3.12+) and TypeScript implementations with no external dependencies. Just standard library HTTP clients.

### 🎯 **Dual SDK Support**

**Python:**
```python
from automagik_telemetry import AutomagikTelemetry

client = AutomagikTelemetry(project_name="my-app", version="1.0.0")
client.track_event("api.request", {"endpoint": "/users", "status": 200})
```

**TypeScript:**
```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const client = new AutomagikTelemetry({ projectName: 'my-app', version: '1.0.0' });
client.trackEvent('api.request', { endpoint: '/users', status: 200 });
```

### 📝 **Structured Logging**

Built-in OTLP-compatible logging with severity levels and structured context.

**Python:**
```python
from automagik_telemetry import AutomagikTelemetry, LogSeverity

client = AutomagikTelemetry(project_name="my-app", version="1.0.0")

# Log with severity levels
client.track_log("User authentication successful", LogSeverity.INFO, {
    "user_id": "anonymous-uuid",
    "method": "oauth"
})

client.track_log("Database connection slow", LogSeverity.WARN, {
    "latency_ms": 1500,
    "threshold_ms": 1000
})

client.track_log("Payment processing failed", LogSeverity.ERROR, {
    "error_code": "PAY-1001",
    "transaction_id": "tx_abc123"
})
```

**TypeScript:**
```typescript
import { AutomagikTelemetry, LogSeverity } from '@automagik/telemetry';

const client = new AutomagikTelemetry({ projectName: 'my-app', version: '1.0.0' });

// Log with severity levels
client.trackLog('User authentication successful', LogSeverity.INFO, {
    userId: 'anonymous-uuid',
    method: 'oauth'
});

client.trackLog('Database connection slow', LogSeverity.WARN, {
    latency_ms: 1500,
    threshold_ms: 1000
});

client.trackLog('Payment processing failed', LogSeverity.ERROR, {
    error_code: 'PAY-1001',
    transaction_id: 'tx_abc123'
});
```

**Available Log Severity Levels:**
- `TRACE` (1) - Finest granularity, debugging information
- `DEBUG` (5) - Detailed debugging information
- `INFO` (9) - Informational messages (default)
- `WARN` (13) - Warning messages
- `ERROR` (17) - Error events
- `FATAL` (21) - Critical errors causing shutdown

**When to Use: Logs vs Events vs Metrics**

| Signal Type | Purpose | Use Case | Example |
|-------------|---------|----------|---------|
| **Events (Traces)** | Track discrete occurrences | User actions, API requests, feature usage | `user.login`, `api.request`, `feature.used` |
| **Metrics** | Track numeric measurements over time | Performance, resource usage, business KPIs | `api.latency_ms`, `memory.usage_mb`, `revenue.total` |
| **Logs** | Capture diagnostic messages with context | Application state, debugging, audit trails | `"User authentication successful"`, `"Database connection failed"` |

**Best Practices:**
- Use **Events** to track what happened (discrete occurrences)
- Use **Metrics** to track how much/how many (quantitative data)
- Use **Logs** to explain why/how it happened (contextual information)
- Combine all three for comprehensive observability

### 🧪 **100% Test Coverage**
Every SDK maintains 100% code coverage with comprehensive unit, integration, and performance tests.

### 🌐 **Production-Ready**
Async by default, automatic batching, retry logic, timeout handling, and graceful degradation when telemetry is unavailable.

---

## 📊 Architecture

### How It Works

**Option 1: OTLP Backend (Default - Production)**
```
Your Application → AutomagikTelemetry SDK → OTLP/HTTP → OpenTelemetry Collector → Prometheus/Grafana
                         ↓
                  Privacy Checks
                  Environment Detection
                  Async Batching
```

**Option 2: ClickHouse Backend (Self-Hosting)**
```
Your Application → AutomagikTelemetry SDK → ClickHouse HTTP API → ClickHouse → Grafana
                         ↓
                  Privacy Checks
                  Environment Detection
                  Batch Processing
                  Compression
```

### Backend Comparison

| Feature | OTLP Backend | ClickHouse Backend |
|---------|--------------|-------------------|
| **Use Case** | Production SaaS | Self-hosted, Local dev |
| **Protocol** | OTLP over HTTP | ClickHouse HTTP API |
| **Components** | SDK → Collector → Storage | SDK → ClickHouse (direct) |
| **Dependencies** | OpenTelemetry Collector | ClickHouse only |
| **Performance** | Standard | Optimized (batching + compression) |
| **Setup Complexity** | Medium | Simple |
| **Data Control** | Collector-managed | Full control |

### Components

| Component | Purpose | Default Endpoint |
|-----------|---------|------------------|
| **SDK** | Client library for your application | N/A |
| **OTLP/HTTP** | Standard telemetry protocol | `https://telemetry.namastex.ai` |
| **ClickHouse HTTP** | Direct ClickHouse insertion | `http://localhost:8123` |
| **Collector** | Receives and processes OTLP telemetry | Configured endpoint |
| **ClickHouse** | High-performance OLAP database | Backend storage |
| **Prometheus** | Stores metrics (OTLP path) | Backend storage |
| **Grafana** | Visualizes metrics | Visualization layer |

### Privacy Controls

```python
# Environment-based auto-disable
ENVIRONMENT=development          # Telemetry disabled
ENVIRONMENT=production          # Telemetry enabled

# Explicit disable
AUTOMAGIK_TELEMETRY_ENABLED=false

# Custom endpoint
AUTOMAGIK_TELEMETRY_ENDPOINT=https://your-collector.com
```

---

## 📦 Quick Start

### Python SDK

**Prerequisites:**
- Python 3.12+

**Installation:**
```bash
pip install automagik-telemetry
```

**Basic Usage:**
```python
from automagik_telemetry import AutomagikTelemetry, StandardEvents

# Initialize client
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Track events (traces)
# 💡 TIP: Use StandardEvents constants for consistent event names!
client.track_event(StandardEvents.FEATURE_USED, {
    "feature_name": "user_authentication",
    "feature_category": "security",
    "method": "oauth"
})

# Track metrics (counters, gauges, histograms)
from automagik_telemetry import MetricType

client.track_metric("api.requests", value=1, metric_type=MetricType.COUNTER, attributes={
    "endpoint": "/api/users",
    "status": 200
})

client.track_metric("system.memory_mb", value=512.5, metric_type=MetricType.GAUGE)

client.track_metric("api.response_time_ms", value=125.3, metric_type=MetricType.HISTOGRAM)

# Track logs with severity levels
from automagik_telemetry import LogSeverity

client.track_log("Application started successfully", LogSeverity.INFO)

client.track_log("Cache miss rate high", LogSeverity.WARN, {
    "cache_hit_rate": 0.45,
    "threshold": 0.80
})

client.track_log("Database connection failed", LogSeverity.ERROR, {
    "error": "connection_timeout",
    "retry_count": 3
})
```

**🔧 Python Initialization: Simple vs Advanced**

Python supports **TWO initialization styles**. Choose based on your needs:

| When to Use | Style | Parameters Available |
|-------------|-------|---------------------|
| Quick start, prototyping, defaults are fine | **Direct Parameters** | 5 basic params only: `project_name`, `version`, `endpoint`, `organization`, `timeout`. Uses optimal defaults: `batch_size=100`, `compression_enabled=True` |
| Production, custom batching, ClickHouse | **TelemetryConfig** | ALL 20+ params including `batch_size`, `compression_enabled`, `backend`, `clickhouse_*`, etc. |

**Simple Style (Direct Parameters):**
```python
# ✅ Best for: Quick start, simple projects
# ℹ️ Uses defaults: batch_size=100, compression_enabled=True
# ⚠️ Limitations: Cannot customize batching, compression, or use ClickHouse backend

client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    endpoint="https://custom.com",  # Optional
    timeout=10  # Optional
)
```

**Advanced Style (TelemetryConfig):**
```python
from automagik_telemetry import TelemetryConfig

# ✅ Best for: Production apps, custom configuration
# ✅ Provides: Full control over batching, compression, ClickHouse, etc.

config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",

    # Customize performance features (direct params use these defaults)
    batch_size=200,  # Custom batch size (default: 100)
    compression_enabled=True,  # Gzip compression (default: True)
    flush_interval=5.0,  # Auto-flush every 5 seconds (default: 5.0)

    # ClickHouse backend (NOT available with direct params!)
    backend="clickhouse",
    clickhouse_endpoint="http://localhost:8123"
)

client = AutomagikTelemetry(config=config)
```

**Migration Path:**
```python
# Start simple (uses default batch_size=100)
client = AutomagikTelemetry(project_name="my-app", version="1.0.0")

# Upgrade when you need to customize batching/compression/ClickHouse
from automagik_telemetry import TelemetryConfig
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    batch_size=200,  # Customize batch size (default: 100)
    compression_enabled=True,  # Customize compression (default: True)
    backend="clickhouse"  # Use ClickHouse backend
)
client = AutomagikTelemetry(config=config)
```

> **💡 TIP:** Start with direct parameters for quick prototyping (uses optimal defaults: `batch_size=100`, `compression_enabled=True`). Migrate to `TelemetryConfig` when you need to customize batching, compression settings, or use ClickHouse backend.
>
> 📚 **Full Guide:** See [Python Initialization Guide](docs/PYTHON_INITIALIZATION_GUIDE.md) for complete details, decision trees, and examples.

### TypeScript SDK

**Prerequisites:**
- Node.js 18+

**Installation:**
```bash
npm install @automagik/telemetry
# or
pnpm add @automagik/telemetry
```

**Basic Usage:**
```typescript
import { AutomagikTelemetry, StandardEvents } from '@automagik/telemetry';

// Initialize client
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Track events
// 💡 TIP: Use StandardEvents constants for consistent event names!
client.trackEvent(StandardEvents.FEATURE_USED, {
    feature_name: 'user_authentication',
    feature_category: 'security',
    method: 'oauth'
});

// Track metrics
import { MetricType } from '@automagik/telemetry';

client.trackMetric('api.requests', 1, MetricType.COUNTER, {
    endpoint: '/api/users',
    status: 200
});

client.trackMetric('system.memory_mb', 512.5, MetricType.GAUGE);

client.trackMetric('api.response_time_ms', 125.3, MetricType.HISTOGRAM);

// Track logs with severity levels
import { LogSeverity } from '@automagik/telemetry';

client.trackLog('Application started successfully', LogSeverity.INFO);

client.trackLog('Cache miss rate high', LogSeverity.WARN, {
    cache_hit_rate: 0.45,
    threshold: 0.80
});

client.trackLog('Database connection failed', LogSeverity.ERROR, {
    error: 'connection_timeout',
    retry_count: 3
});
```

> **💡 Standard Event Constants:** Both SDKs provide `StandardEvents` with predefined constants for consistent tracking:
> - `FEATURE_USED` - Track feature usage across your application
> - `API_REQUEST` - Track API endpoint calls and responses
> - `COMMAND_EXECUTED` - Track CLI command executions
> - `OPERATION_LATENCY` - Track performance metrics and timings
> - `ERROR_OCCURRED` - Track errors and exceptions
> - `SERVICE_HEALTH` - Track service health checks and status
>
> 📚 See [Event Constants Reference](docs/REFERENCES/EVENT_CONSTANTS.md) for complete documentation, naming conventions, and best practices.

### Using ClickHouse Backend (Self-Hosting)

For self-hosted deployments, you can bypass the OTLP Collector and write directly to ClickHouse. This provides better performance and simpler architecture for local development.

**Why Use ClickHouse Backend?**
- Direct insertion to ClickHouse (no middleware)
- Faster for self-hosted setups
- Full control over your telemetry data
- Simpler architecture with fewer components
- Zero additional dependencies (uses stdlib only)

**Python with ClickHouse:**
```python
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig

# Direct ClickHouse backend
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    backend="clickhouse",  # Use ClickHouse instead of OTLP
    clickhouse_endpoint="http://localhost:8123",
    clickhouse_database="telemetry",
    batch_size=100  # Batch database rows before INSERT
)
client = AutomagikTelemetry(config=config)

# Use normally - data goes directly to ClickHouse
client.track_event("user.login", {"user_id": "123"})
```

**TypeScript with ClickHouse:**
```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

// Direct ClickHouse backend
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    backend: 'clickhouse',  // Use ClickHouse instead of OTLP
    clickhouseEndpoint: 'http://localhost:8123',
    clickhouseDatabase: 'telemetry',
    batchSize: 100  // Batch database rows before INSERT
});

// Use normally - data goes directly to ClickHouse
client.trackEvent('user.login', { userId: '123' });
```

**When to Use Which Backend:**

| Use Case | Backend | Why |
|----------|---------|-----|
| Production SaaS | `otlp` (default) | Managed infrastructure, standard protocol |
| Self-hosted | `clickhouse` | Direct control, better performance |
| Local development | `clickhouse` | Simple setup, instant feedback |
| Multi-cloud | `otlp` | Flexibility to change backends |

### Configuration

**Complete Configuration Reference**

All available configuration parameters with their defaults:

| Parameter | Python | TypeScript | Default (Python) | Default (TypeScript) | Description |
|-----------|--------|------------|------------------|----------------------|-------------|
| `project_name` / `projectName` | ✅ | ✅ | *Required* | *Required* | Name of your project |
| `version` | ✅ | ✅ | *Required* | *Required* | Project version |
| `backend` | ✅ | ✅ | `"otlp"` | `"otlp"` | Backend type: `"otlp"` or `"clickhouse"` |
| `endpoint` | ✅ | ✅ | `"https://telemetry.namastex.ai/v1/traces"` | `"https://telemetry.namastex.ai/v1/traces"` | Main traces endpoint |
| `organization` | ✅ | ✅ | `"namastex"` | `"namastex"` | Organization name |
| `timeout` | ✅ | ✅ | `5` (seconds) | `5` (seconds) | HTTP request timeout |
| `batch_size` / `batchSize` | ✅ | ✅ | `100` | `100` | OTLP: events queued; ClickHouse: rows batched |
| `flush_interval` / `flushInterval` | ✅ | ✅ | `5.0` (seconds) | `5000` (milliseconds) | Auto-flush interval |
| `compression_enabled` / `compressionEnabled` | ✅ | ✅ | `True` | `true` | Enable gzip compression |
| `compression_threshold` / `compressionThreshold` | ✅ | ✅ | `1024` (bytes) | `1024` (bytes) | Minimum size for compression |
| `max_retries` / `maxRetries` | ✅ | ✅ | `3` | `3` | Maximum retry attempts |
| `retry_backoff_base` / `retryBackoffBase` | ✅ | ✅ | `1.0` (seconds) | `1000` (milliseconds) | Base backoff time for retries |
| `metrics_endpoint` / `metricsEndpoint` | ✅ | ✅ | Auto-derived | Auto-derived | Custom metrics endpoint |
| `logs_endpoint` / `logsEndpoint` | ✅ | ✅ | Auto-derived | Auto-derived | Custom logs endpoint |

**Understanding batch_size**

The `batch_size` parameter controls batching but works differently per backend:

**OTLP Backend:**
- Controls how many **events** are queued in memory before sending an HTTP request
- Example: `batch_size=100` means send HTTP POST after 100 events queued
- Python default: `100` (optimized for performance)
- TypeScript default: `100` (optimized for batch processing)

**ClickHouse Backend:**
- Controls how many **rows** are batched before executing a database INSERT
- Example: `batch_size=100` means execute INSERT after 100 rows accumulated
- Default: `100` (both Python and TypeScript)

Both Python and TypeScript SDKs now default to `batch_size=100` for optimal performance:

- **Python SDK:** `batch_size=100` (batched send) - Reduces HTTP overhead, optimal performance
- **TypeScript SDK:** `batchSize=100` (batched send) - Optimized for high-volume web applications

**Performance Benefits:**
- Batches up to 100 events before sending
- Automatic flush every 5 seconds ensures low latency
- Significantly reduces HTTP request overhead
- Better network utilization

**For immediate send (testing/debugging):**
```python
# Python - disable batching for testing
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    batch_size=1  # Send immediately, useful for testing
)
```

**TypeScript - disable batching for testing:**
```typescript
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    batchSize: 1  // Send immediately, useful for testing
});
```

**Environment Variables (OTLP Backend - Default):**
```bash
# Enable/disable telemetry (default: false, opt-in required)
export AUTOMAGIK_TELEMETRY_ENABLED=true

# Custom OTLP endpoint (default: https://telemetry.namastex.ai)
export AUTOMAGIK_TELEMETRY_ENDPOINT=https://your-collector.com

# Custom metrics endpoint (optional, auto-derived from base endpoint)
export AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT=https://your-collector.com/v1/metrics

# Custom logs endpoint (optional, auto-derived from base endpoint)
export AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT=https://your-collector.com/v1/logs

# HTTP timeout in seconds (default: 5)
export AUTOMAGIK_TELEMETRY_TIMEOUT=10

# Enable verbose logging for debugging (default: false)
export AUTOMAGIK_TELEMETRY_VERBOSE=true

# Auto-disable in development/test environments
export ENVIRONMENT=development
```

**Environment Variables (ClickHouse Backend):**
```bash
# Use ClickHouse backend instead of OTLP
export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse

# ClickHouse endpoint (default: http://localhost:8123)
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://localhost:8123

# ClickHouse database name (default: telemetry)
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE=telemetry

# ClickHouse table name (default: traces, Python only)
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE=traces

# Optional ClickHouse authentication
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME=default
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD=your-password
```

**Code Configuration (OTLP - Basic):**
```python
# Python
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    endpoint="https://custom-collector.com",  # Optional
    organization="my-org"  # Optional
)
```

```typescript
// TypeScript
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    endpoint: 'https://custom-collector.com',  // Optional
    organization: 'my-org'  // Optional
});
```

**Code Configuration (OTLP - Advanced):**
```python
# Python - Advanced configuration with all options
from automagik_telemetry import TelemetryConfig, AutomagikTelemetry

config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    organization="my-org",

    # Endpoints
    endpoint="https://telemetry.example.com/v1/traces",
    metrics_endpoint="https://telemetry.example.com/v1/metrics",  # Optional override
    logs_endpoint="https://telemetry.example.com/v1/logs",  # Optional override

    # Performance
    batch_size=100,  # Batch 100 events before sending
    flush_interval=5.0,  # Auto-flush every 5 seconds
    timeout=10,  # 10 seconds timeout

    # Compression
    compression_enabled=True,
    compression_threshold=1024,  # Compress payloads > 1KB

    # Reliability
    max_retries=3,
    retry_backoff_base=1.0  # 1 second base backoff
)

client = AutomagikTelemetry(config=config)
```

```typescript
// TypeScript - Advanced configuration with all options
import { AutomagikTelemetry } from '@automagik/telemetry';

const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    organization: 'my-org',

    // Endpoints
    endpoint: 'https://telemetry.example.com/v1/traces',
    metricsEndpoint: 'https://telemetry.example.com/v1/metrics',  // Optional override
    logsEndpoint: 'https://telemetry.example.com/v1/logs',  // Optional override

    // Performance
    batchSize: 100,  // Batch 100 events before sending
    flushInterval: 5000,  // Auto-flush every 5 seconds
    timeout: 10,  // 10 seconds timeout

    // Compression
    compressionEnabled: true,
    compressionThreshold: 1024,  // Compress payloads > 1KB

    // Reliability
    maxRetries: 3,
    retryBackoffBase: 1000  // 1 second base backoff
});
```

**Code Configuration (ClickHouse):**
```python
# Python
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    backend="clickhouse",
    clickhouse_endpoint="http://localhost:8123",
    clickhouse_database="telemetry",
    clickhouse_username="default",  # Optional
    clickhouse_password="",  # Optional
    batch_size=100,  # Optional (default: 100 for both Python and TypeScript)
    compression_enabled=True  # Optional (default: True)
)
client = AutomagikTelemetry(config=config)
```

```typescript
// TypeScript
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    backend: 'clickhouse',
    clickhouseEndpoint: 'http://localhost:8123',
    clickhouseDatabase: 'telemetry',
    clickhouseUsername: 'default',  // Optional
    clickhousePassword: '',  // Optional
    batchSize: 100,  // Optional (default: 100 for TypeScript)
    compressionEnabled: true  // Optional (default: true)
});
```

---

## 🔄 SDK Differences

While both SDKs provide identical functionality, there are intentional differences in defaults and conventions:

### Naming Conventions
- **Python**: Uses `snake_case` following PEP 8 conventions
  - `track_event`, `project_name`, `flush_interval`
- **TypeScript**: Uses `camelCase` following JavaScript conventions
  - `trackEvent`, `projectName`, `flushInterval`

### Batch Size Defaults
Both SDKs now use `batch_size=100` by default for optimal performance:

- **Python**: `batch_size=100` (batched)
  - Optimized for performance with automatic batching
  - Up to 100 events queued before sending
  - Automatic flush every 5 seconds
  - Significantly reduces HTTP overhead
- **TypeScript**: `batchSize=100` (batched)
  - Optimized for performance in high-throughput scenarios
  - Reduces network overhead with batching
  - Better for modern async applications

**For immediate send (testing/debugging):**
```python
# Python - disable batching for testing
client = AutomagikTelemetry(
    project_name="my-app",
    batch_size=1  # Send immediately for testing/debugging
)
```

```typescript
// TypeScript - disable batching for testing
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    batchSize: 1  // Send immediately for testing/debugging
});
```

### Time Units
- **Python**: `flush_interval` in **seconds** (float)
  ```python
  flush_interval=5.0  # 5 seconds
  ```
- **TypeScript**: `flushInterval` in **milliseconds** (number)
  ```typescript
  flushInterval: 5000  // 5 seconds
  ```

### Async Patterns
- **Python**: Provides both sync and async methods
  ```python
  client.track_event("event", {})  # Sync
  await client.track_event_async("event", {})  # Async
  ```
- **TypeScript**: All methods return void but are internally async
  ```typescript
  client.trackEvent('event', {});  // Fire-and-forget
  ```

---

## 🔧 Advanced Usage

### Custom Attributes

Add context to every metric and event:

```python
# Python
client.track_event("payment.processed", {
    "amount": 99.99,
    "currency": "USD",
    "payment_method": "card",
    "success": True
})
```

```typescript
// TypeScript
client.trackEvent('payment.processed', {
    amount: 99.99,
    currency: 'USD',
    paymentMethod: 'card',
    success: true
});
```

### Error Tracking

Track errors without exposing sensitive data:

```python
# Python
try:
    risky_operation()
except Exception as e:
    client.track_event("error.occurred", {
        "error_type": type(e).__name__,
        "module": "payment_processor",
        "recoverable": False
    })
```

### Performance Monitoring

Track response times and resource usage:

```python
# Python
import time
from automagik_telemetry import MetricType

start = time.time()
process_request()
duration_ms = (time.time() - start) * 1000

client.track_metric(
    metric_name="request.duration_ms",
    value=duration_ms,
    metric_type=MetricType.HISTOGRAM,
    attributes={"endpoint": "/api/process", "method": "POST"}
)
```

### Switching Between Backends

You can easily switch between OTLP and ClickHouse backends based on your environment:

```python
# Python - Environment-based backend selection
import os

backend = os.getenv("TELEMETRY_BACKEND", "otlp")

if backend == "clickhouse":
    client = AutomagikTelemetry(
        project_name="my-app",
        version="1.0.0",
        backend="clickhouse",
        clickhouse_endpoint=os.getenv("CLICKHOUSE_ENDPOINT", "http://localhost:8123")
    )
else:
    client = AutomagikTelemetry(
        project_name="my-app",
        version="1.0.0",
        endpoint=os.getenv("OTLP_ENDPOINT", "https://telemetry.namastex.ai")
    )

# Use the same API regardless of backend
client.track_event("app.started", {"version": "1.0.0"})
```

```typescript
// TypeScript - Environment-based backend selection
const backend = process.env.TELEMETRY_BACKEND || 'otlp';

const client = backend === 'clickhouse'
  ? new AutomagikTelemetry({
      projectName: 'my-app',
      version: '1.0.0',
      backend: 'clickhouse',
      clickhouseEndpoint: process.env.CLICKHOUSE_ENDPOINT || 'http://localhost:8123'
    })
  : new AutomagikTelemetry({
      projectName: 'my-app',
      version: '1.0.0',
      endpoint: process.env.OTLP_ENDPOINT || 'https://telemetry.namastex.ai'
    });

// Use the same API regardless of backend
client.trackEvent('app.started', { version: '1.0.0' });
```


---

## 🎛️ Control Methods

### Flush - Force Immediate Send

Force all queued events to be sent immediately. Useful before application shutdown or at critical checkpoints.

**Python:**
```python
from automagik_telemetry import AutomagikTelemetry

client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    batch_size=100  # Events will queue until batch_size or flush
)

# Track some events
client.track_event("app.startup")
client.track_metric("initialization_time_ms", 1234.5)

# Force immediate send (synchronous)
client.flush()

# For async contexts
import asyncio
await client.flush_async()
```

**TypeScript:**
```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    batchSize: 100  // Events will queue until batchSize or flush
});

// Track some events
client.trackEvent('app.startup');
client.trackMetric('initialization_time_ms', 1234.5);

// Force immediate send (async)
await client.flush();
```

**When to use `flush()`:**
- Before application shutdown to ensure no data loss
- After critical events that must be delivered
- At checkpoints in long-running processes
- When using batching (`batch_size` > 1) and need immediate delivery

### Enable/Disable - Runtime Control

Enable or disable telemetry programmatically at runtime.

**Python:**
```python
from automagik_telemetry import AutomagikTelemetry

client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Enable telemetry (removes opt-out file)
client.enable()

# Track events - now active
client.track_event("user.action")

# Disable telemetry (creates opt-out file)
client.disable()
```

**TypeScript:**
```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Enable telemetry (removes opt-out file)
client.enable();

// Track events - now active
client.trackEvent('user.action');

// Disable telemetry (creates opt-out file, flushes pending events)
await client.disable();  // Flushes before disabling
```

**What happens when you disable:**
- Pending events are flushed before disabling (TypeScript only)
- Creates `~/.automagik-no-telemetry` opt-out file
- All future tracking calls become no-ops (silent failures)
- Preference persists across application restarts

### Check Status - isEnabled() and getStatus()

Check if telemetry is enabled and get detailed status information.

**Python:**
```python
from automagik_telemetry import AutomagikTelemetry

client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Simple enabled check
if client.is_enabled():
    print("Telemetry is active")
    client.track_event("conditional.event")
else:
    print("Telemetry is disabled")

# Detailed status information
status = client.get_status()
print(f"Enabled: {status['enabled']}")
print(f"User ID: {status['user_id']}")
print(f"Session ID: {status['session_id']}")
print(f"Endpoint: {status['endpoint']}")
print(f"Batch size: {status['batch_size']}")
print(f"Queue sizes: {status['queue_sizes']}")
# Output:
# {
#     'enabled': True,
#     'user_id': 'uuid-here',
#     'session_id': 'uuid-here',
#     'project_name': 'my-app',
#     'project_version': '1.0.0',
#     'endpoint': 'https://telemetry.namastex.ai/v1/traces',
#     'metrics_endpoint': 'https://telemetry.namastex.ai/v1/metrics',
#     'logs_endpoint': 'https://telemetry.namastex.ai/v1/logs',
#     'opt_out_file_exists': False,
#     'env_var': None,
#     'verbose': False,
#     'batch_size': 100,
#     'compression_enabled': True,
#     'queue_sizes': {
#         'traces': 5,
#         'metrics': 2,
#         'logs': 0
#     }
# }
```

**TypeScript:**
```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Simple enabled check
if (client.isEnabled()) {
    console.log('Telemetry is active');
    client.trackEvent('conditional.event');
} else {
    console.log('Telemetry is disabled');
}

// Detailed status information
const status = client.getStatus();
console.log(`Enabled: ${status.enabled}`);
console.log(`User ID: ${status.user_id}`);
console.log(`Session ID: ${status.session_id}`);
console.log(`Endpoint: ${status.endpoint}`);
// Output:
// {
//     enabled: true,
//     user_id: 'uuid-here',
//     session_id: 'uuid-here',
//     project_name: 'my-app',
//     project_version: '1.0.0',
//     endpoint: 'https://telemetry.namastex.ai/v1/traces',
//     opt_out_file_exists: false,
//     env_var: undefined,
//     verbose: false
// }
```

**Use cases for status checking:**
- Debugging telemetry configuration issues
- Displaying telemetry state in admin dashboards
- Conditional tracking based on enabled state
- Monitoring queue sizes to tune batch configuration

---

## ⚡ Async Support (Python)

The Python SDK provides async versions of all tracking methods for seamless integration with asyncio applications.

### Available Async Methods

All tracking methods have async counterparts that run in a thread pool to avoid blocking the event loop:

- `track_event_async()` - Async event tracking
- `track_error_async()` - Async error tracking
- `track_metric_async()` - Async metric tracking
- `track_log_async()` - Async log tracking
- `flush_async()` - Async flush

### Usage Examples

**Basic Async Tracking:**
```python
import asyncio
from automagik_telemetry import AutomagikTelemetry, MetricType, LogSeverity

client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

async def main():
    # Async event tracking
    await client.track_event_async("user.login", {
        "user_id": "anonymous-123",
        "method": "oauth"
    })

    # Async metric tracking
    await client.track_metric_async(
        "api.latency_ms",
        123.45,
        MetricType.HISTOGRAM,
        {"endpoint": "/api/users"}
    )

    # Async log tracking
    await client.track_log_async(
        "User authenticated successfully",
        LogSeverity.INFO,
        {"user_type": "premium"}
    )

    # Async error tracking
    try:
        raise ValueError("Test error")
    except Exception as e:
        await client.track_error_async(e, {
            "context": "authentication",
            "recoverable": True
        })

    # Async flush
    await client.flush_async()

asyncio.run(main())
```

**FastAPI Integration:**
```python
from fastapi import FastAPI
from automagik_telemetry import AutomagikTelemetry, MetricType
import time

app = FastAPI()
client = AutomagikTelemetry(project_name="my-api", version="1.0.0")

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    start = time.time()

    try:
        # Your async logic here
        user = await fetch_user(user_id)
        duration_ms = (time.time() - start) * 1000

        # Track async
        await client.track_event_async("api.request", {
            "endpoint": f"/users/{user_id}",
            "status": 200
        })

        await client.track_metric_async(
            "api.latency_ms",
            duration_ms,
            MetricType.HISTOGRAM
        )

        return user

    except Exception as e:
        await client.track_error_async(e, {
            "endpoint": f"/users/{user_id}"
        })
        raise

@app.on_event("shutdown")
async def shutdown_event():
    # Ensure all events are sent before shutdown
    await client.flush_async()
```

**Async Context Manager Pattern:**
```python
import asyncio
from automagik_telemetry import AutomagikTelemetry

async def tracked_operation(client: AutomagikTelemetry):
    """Example of tracking an async operation."""
    await client.track_event_async("operation.start")

    try:
        # Your async work here
        result = await do_async_work()

        await client.track_event_async("operation.success", {
            "result_count": len(result)
        })

        return result

    except Exception as e:
        await client.track_error_async(e)
        raise

    finally:
        # Ensure events are sent
        await client.flush_async()
```

**Why Use Async Methods:**
- Non-blocking execution in async applications
- Better integration with FastAPI, aiohttp, etc.
- Maintains event loop responsiveness
- Proper async/await semantics
- No need for `asyncio.to_thread()` wrapper

**Note:** Async methods use `asyncio.to_thread()` internally, so they're safe to use in any async context without blocking the event loop.
```

---

## 🏗️ Self-Hosting & Local Development

Want to run your own telemetry infrastructure? We've got you covered!

```bash
cd infra
make start        # Start all services (ClickHouse + Collector + Grafana)
make test         # Send test data
make dashboard    # Open Grafana dashboard
```

**What you get:**
- 🗄️ **ClickHouse** - High-performance OLAP database for telemetry data
- 📡 **OTLP Collector** - Receives and processes OTLP telemetry
- 📊 **Grafana** - Pre-configured dashboards for visualization
- 🚀 **Production-ready** - Docker Compose setup with best practices

**Two Backend Options:**

1. **OTLP Collector Path** (Standard)
   - Use default SDK configuration
   - Data flows through OpenTelemetry Collector
   - Best for production-like environments

2. **Direct ClickHouse Path** (Recommended for Self-Hosting)
   - Use `backend="clickhouse"` in SDK configuration
   - Bypasses collector, writes directly to ClickHouse
   - Simpler, faster, fewer components
   - See [ClickHouse Backend Design](infra/CLICKHOUSE_BACKEND_DESIGN.md)

**Full documentation:** [infra/README.md](infra/README.md)

**Quick links:**
- [Architecture Overview](infra/README.md#-architecture)
- [Configuration Guide](infra/README.md#-configuration)
- [Production Deployment](infra/README.md#-production-deployment)
- [Scaling Guidelines](infra/README.md#-scaling)
- [Troubleshooting](infra/README.md#-troubleshooting)

---

## 📚 Documentation

**📍 Start Here:** [Documentation Index](docs/INDEX.md) - Complete navigation hub

### 🚀 Getting Started
- **[Quick Start Guide](docs/GETTING_STARTED.md)** - Get running in 5 minutes
- **[Configuration Guide](docs/USER_GUIDES/CONFIGURATION.md)** - All configuration options
- **[Privacy & Security](docs/USER_GUIDES/PRIVACY.md)** - Privacy-first design explained

### 👨‍💻 User Guides
- **[Backends Guide](docs/USER_GUIDES/BACKENDS.md)** - OTLP vs ClickHouse comparison
- **[Self-Hosting](docs/USER_GUIDES/SELF_HOSTING.md)** - Run your own infrastructure
- **[Quick Reference](docs/USER_GUIDES/QUICK_REFERENCE.md)** - Commands and patterns cheat sheet

### 🔧 Developer Guides
- **[Architecture](docs/DEVELOPER_GUIDES/ARCHITECTURE.md)** - System design deep dive
- **[Implementation](docs/DEVELOPER_GUIDES/IMPLEMENTATION.md)** - Integration patterns
- **[Testing](docs/DEVELOPER_GUIDES/TESTING.md)** - Test strategies and CI/CD
- **[SDK Differences](docs/DEVELOPER_GUIDES/SDK_DIFFERENCES.md)** - Python vs TypeScript
- **[Contributing](docs/DEVELOPER_GUIDES/CONTRIBUTING.md)** - How to contribute

### 📖 References
- **[API Reference](docs/REFERENCES/API_REFERENCE.md)** - Complete API documentation
- **[Environment Variables](docs/REFERENCES/ENVIRONMENT_VARIABLES.md)** - All env vars
- **[Troubleshooting](docs/REFERENCES/TROUBLESHOOTING.md)** - Common issues & solutions

**Need help?** Check the [Documentation Index](docs/INDEX.md) for the complete navigation.

---

## 🛠️ Development

### Python Development

```bash
# Clone repository
git clone https://github.com/namastexlabs/automagik-telemetry.git
cd automagik-telemetry/python

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=automagik_telemetry --cov-report=html

# Type checking
mypy src/automagik_telemetry

# Linting
ruff check src tests
```

### TypeScript Development

```bash
# Navigate to TypeScript directory
cd typescript

# Install dependencies
pnpm install

# Build
pnpm build

# Run tests
pnpm test

# Run tests with coverage
pnpm test -- --coverage

# Linting
pnpm lint
```

### Running Integration Tests

```bash
# Python integration tests
cd python
pytest tests/integration/

# TypeScript integration tests
cd typescript
pnpm test -- --testPathPattern=integration
```

### Testing Against Local Collector

```bash
# Start local OpenTelemetry Collector
docker run -p 4318:4318 -p 4317:4317 \
  otel/opentelemetry-collector-contrib:0.128.0

# Test Python SDK
python3 test_telemetry_local.py http://localhost:4318

# Test TypeScript SDK
cd typescript && pnpm test
```

---

## 🗺️ Roadmap

### Completed ✅
- [x] Python SDK with 100% test coverage
- [x] TypeScript SDK with 100% test coverage
- [x] OTLP/HTTP protocol support
- [x] Privacy-first design with opt-in defaults
- [x] Zero-dependency implementation
- [x] Prometheus integration
- [x] Production OpenTelemetry Collector
- [x] Cloudflare tunnel for secure access
- [x] Comprehensive documentation

### Next Up 🚀
- [ ] **Metrics Visualization** - Pre-built Grafana dashboards
- [ ] **Trace Visualization** - Jaeger integration for distributed tracing
- [ ] **Sampling Configuration** - Configurable sampling rates for high-volume apps
- [ ] **Batch Configuration** - Customizable batch size and timeout
- [ ] **OpenTelemetry SDK Integration** - Full OTEL SDK compatibility mode
- [ ] **Custom Exporters** - Support for additional backends (DataDog, New Relic)

### Future Vision 🌟
- [ ] **Browser SDK** - JavaScript SDK for frontend telemetry
- [ ] **Mobile SDKs** - iOS and Android support
- [ ] **Real User Monitoring** - RUM metrics and session replay
- [ ] **APM Features** - Application Performance Monitoring
- [ ] **Distributed Tracing** - Cross-service trace correlation
- [ ] **Anomaly Detection** - ML-powered anomaly detection

---

## 🧪 Testing Philosophy

We maintain **100% test coverage** across both SDKs with:

- **Unit Tests** - Every function, every edge case
- **Integration Tests** - End-to-end OTLP communication
- **Performance Tests** - Overhead benchmarks < 1ms per operation
- **Privacy Tests** - Verify no PII leakage
- **Reliability Tests** - Graceful degradation when collector is down

**Coverage Reports:**
- Python: 100% (all modules)
- TypeScript: 100% (all modules)

**Test Commands:**
```bash
# Python - Generate coverage report
cd python && pytest --cov=automagik_telemetry --cov-report=html
# View at python/htmlcov/index.html

# TypeScript - Generate coverage report
cd typescript && pnpm test -- --coverage
# View at typescript/coverage/lcov-report/index.html
```

---

## 🤝 Contributing

We love contributions! However, to maintain project quality:

1. **Discuss First**: Open an issue before starting work
2. **Maintain 100% Coverage**: All new code must have tests
3. **Follow Standards**: Match existing code patterns
4. **Test Thoroughly**: Run full test suite before submitting
5. **Document Well**: Update docs with your changes
6. **Privacy First**: Never add features that compromise privacy

### Development Standards

**Python:**
- Type hints required (mypy strict mode)
- Ruff for linting and formatting
- pytest for testing
- 100% test coverage enforced

**TypeScript:**
- Strict TypeScript configuration
- ESLint + Prettier for code quality
- Jest for testing
- 100% test coverage enforced

---

## 🙏 Acknowledgments

Built with love by [Namastex Labs](https://namastex.ai) using:
- [OpenTelemetry](https://opentelemetry.io/) - The industry standard for observability
- [Prometheus](https://prometheus.io/) - Metrics storage and querying
- [Grafana](https://grafana.com/) - Metrics visualization
- [Python](https://python.org/) - Python 3.12+
- [TypeScript](https://www.typescriptlang.org/) - TypeScript 5.4+

Special thanks to the OpenTelemetry community for creating the standard protocol that makes this SDK possible.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **GitHub**: [github.com/namastexlabs/automagik-telemetry](https://github.com/namastexlabs/automagik-telemetry)
- **PyPI**: [pypi.org/project/automagik-telemetry](https://pypi.org/project/automagik-telemetry)
- **npm**: [npmjs.com/package/@automagik/telemetry](https://www.npmjs.com/package/@automagik/telemetry)
- **Discord**: [discord.gg/xcW8c7fF3R](https://discord.gg/xcW8c7fF3R)
- **Twitter**: [@namastexlabs](https://twitter.com/namastexlabs)
- **DeepWiki Docs**: [deepwiki.com/namastexlabs/automagik-telemetry](https://deepwiki.com/namastexlabs/automagik-telemetry)

---

<p align="center">
  <strong>🚀 Privacy-first telemetry. Zero dependencies. 100% coverage. Production-ready.</strong><br>
  <strong>Built for developers who care about privacy and performance.</strong><br><br>
  <a href="https://github.com/namastexlabs/automagik-telemetry">Star us on GitHub</a> •
  <a href="https://discord.gg/xcW8c7fF3R">Join our Discord</a>
</p>

<p align="center">
  Made with ❤️ by <a href="https://namastex.ai">Namastex Labs</a><br>
  <em>AI that elevates human potential, not replaces it</em>
</p>
<a href="https://deepwiki.com/namastexlabs/automagik-telemetry"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
