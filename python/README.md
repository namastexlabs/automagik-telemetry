# Automagik Telemetry - Python SDK

> **📚 [Complete Documentation](../docs/INDEX.md)** | **🚀 [Main README](../README.md)** | **⚙️ [Configuration Guide](../docs/USER_GUIDES/CONFIGURATION.md)**

Privacy-first OpenTelemetry SDK for Python applications with zero dependencies and 100% test coverage.

## Installation

```bash
pip install automagik-telemetry
```

**Requirements:** Python 3.12+

## Quick Start

```python
from automagik_telemetry import AutomagikTelemetry, MetricType

# Initialize client
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Track events (traces)
client.track_event("user.login", {
    "user_id": "anonymous-123",
    "method": "oauth"
})

# Track metrics (counter, gauge, histogram)
client.track_metric("api.requests", value=1, metric_type=MetricType.COUNTER, attributes={
    "endpoint": "/api/users",
    "status": 200
})
```

## Key Configuration

### Batch Size (Default: `batch_size=1`)

```python
# Default: Send immediately (low latency)
client = AutomagikTelemetry(project_name="my-app", version="1.0.0")

# Enable batching for high-volume apps
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    batch_size=100  # Batch 100 events before sending
)
```

### Backend Selection

```python
# OTLP Backend (default - production)
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    endpoint="https://telemetry.namastex.ai"
)

# ClickHouse Backend (self-hosting)
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    backend="clickhouse",
    clickhouse_endpoint="http://localhost:8123"
)
```

### Environment Variables

```bash
# Disable telemetry
export AUTOMAGIK_TELEMETRY_ENABLED=false

# Auto-disable in development
export ENVIRONMENT=development

# Custom OTLP endpoint
export AUTOMAGIK_TELEMETRY_ENDPOINT=https://your-collector.com

# ClickHouse backend
export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://localhost:8123
```

See [Configuration Guide](../docs/USER_GUIDES/CONFIGURATION.md) for all options.

## Development

```bash
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

## Documentation

- **[Getting Started](../docs/GETTING_STARTED.md)** - Complete setup guide
- **[Configuration](../docs/USER_GUIDES/CONFIGURATION.md)** - All configuration options
- **[Backends Guide](../docs/USER_GUIDES/BACKENDS.md)** - OTLP vs ClickHouse comparison
- **[API Reference](../docs/REFERENCES/API_REFERENCE.md)** - Complete API documentation
- **[SDK Differences](../docs/DEVELOPER_GUIDES/SDK_DIFFERENCES.md)** - Python vs TypeScript
- **[Troubleshooting](../docs/REFERENCES/TROUBLESHOOTING.md)** - Common issues and solutions

## Python-Specific Features

- **Sync and async methods:** `track_event()` (sync) and `track_event_async()` (async)
- **snake_case naming:** Follows PEP 8 conventions (`track_event`, `project_name`)
- **Type hints:** Full type safety with mypy strict mode
- **Time units:** `flush_interval` in seconds (float)

See [SDK Differences](../docs/DEVELOPER_GUIDES/SDK_DIFFERENCES.md) for Python vs TypeScript comparison.

## License

MIT - see [LICENSE](../LICENSE) for details.
