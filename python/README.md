# Automagik Telemetry - Python SDK

Privacy-first OpenTelemetry SDK for Python applications.

## Installation

```bash
pip install automagik-telemetry
```

## Quick Start

```python
from automagik_telemetry import AutomagikTelemetry, MetricType

# Initialize client
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Track events
client.track_event("user.login", {
    "user_id": "anonymous-123",
    "method": "oauth"
})

# Track metrics
client.track_metric("api.requests", value=1, metric_type=MetricType.COUNTER, attributes={
    "endpoint": "/api/users",
    "status": 200
})
```

## Configuration

### Batch Size

The Python SDK defaults to `batch_size=1`, which means events are sent immediately to the telemetry backend. This ensures low-latency event delivery but may result in more frequent network requests.

**Enable batching for better performance:**

```python
from automagik_telemetry import AutomagikTelemetry

client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    batch_size=100  # Send events in batches of 100
)
```

**When to use batching:**
- High-volume applications (100+ events/second)
- Performance-sensitive workloads
- Reducing network overhead

**When to use immediate send (batch_size=1):**
- Low-volume applications
- Real-time monitoring requirements
- Debugging and testing

> **Note:** The TypeScript SDK defaults to `batchSize=100` for efficient batching. See [main README](https://github.com/namastexlabs/automagik-telemetry#configuration) for cross-SDK differences.

## Documentation

Full documentation: [github.com/namastexlabs/automagik-telemetry](https://github.com/namastexlabs/automagik-telemetry)

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=automagik_telemetry --cov-report=html
```

## License

MIT - see [LICENSE](../LICENSE) for details.
