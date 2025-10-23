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
