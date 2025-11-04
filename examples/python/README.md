# Python Examples

This directory contains examples demonstrating how to use the Automagik Telemetry Python SDK.

## Prerequisites

```bash
# Install the SDK
pip install automagik-telemetry

# Or install from local source (for development)
pip install -e ../../python
```

## Running Examples

### Basic Example

The simplest way to get started. Shows event tracking, metrics, and logs.

```bash
python basic_example.py
```

### Omni Example

Real-world example showing integration with the Omni messaging system.

```bash
python omni_example.py
```

### Opt-in Testing

Test the opt-in/opt-out functionality.

```bash
python test_opt_in.py
```

## Testing with Local Infrastructure

To test with local ClickHouse and OTLP collector:

```bash
# 1. Start the infrastructure
cd ../../infra
make start

# 2. Wait for services to be ready
make health

# 3. Run the examples with local configuration
cd ../examples/python

# Set environment variables for local testing
export AUTOMAGIK_TELEMETRY_ENABLED=true
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces
export AUTOMAGIK_TELEMETRY_VERBOSE=true

python basic_example.py

# 4. View data in Grafana
# Open http://localhost:3000 in your browser
# Default credentials: admin/admin
```

## Configuration Options

Examples can be configured via environment variables or code:

### Environment Variables

```bash
# Enable/disable telemetry
export AUTOMAGIK_TELEMETRY_ENABLED=true

# Set endpoint (OTLP or ClickHouse)
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces

# Enable verbose logging
export AUTOMAGIK_TELEMETRY_VERBOSE=true

# Set project info
export AUTOMAGIK_TELEMETRY_PROJECT_NAME=my-project
export AUTOMAGIK_TELEMETRY_PROJECT_VERSION=1.0.0

# Configure backend
export AUTOMAGIK_TELEMETRY_BACKEND=otlp  # or "clickhouse"
```

### Code Configuration

```python
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig

config = TelemetryConfig(
    project_name="my-project",
    version="1.0.0",
    endpoint="http://localhost:4318/v1/traces",
    backend="otlp",  # or "clickhouse"
    batch_size=100,
    flush_interval=5.0,
    timeout=5,
    verbose=True,
)

telemetry = AutomagikTelemetry(config=config)
```

## Example Structure

```
examples/python/
├── README.md              # This file
├── basic_example.py       # Simple getting started example
├── omni_example.py        # Real-world Omni integration
└── test_opt_in.py         # Opt-in/opt-out testing
```

## Troubleshooting

### Telemetry not sending data

1. Check if telemetry is enabled:
   ```python
   status = telemetry.get_status()
   print(status['enabled'])
   ```

2. Enable verbose logging:
   ```bash
   export AUTOMAGIK_TELEMETRY_VERBOSE=true
   ```

3. Check opt-out file doesn't exist:
   ```bash
   rm ~/.automagik-no-telemetry
   ```

### Connection refused errors

1. Ensure infrastructure is running:
   ```bash
   cd ../../infra
   make health
   ```

2. Check service ports:
   - OTLP Collector: http://localhost:4318
   - ClickHouse: http://localhost:8123
   - Grafana: http://localhost:3000

### Import errors

1. Ensure SDK is installed:
   ```bash
   pip list | grep automagik
   ```

2. Reinstall if needed:
   ```bash
   pip install --force-reinstall automagik-telemetry
   ```

## Next Steps

- Read the [Getting Started Guide](../../docs/GETTING_STARTED.md)
- Explore [Configuration Options](../../docs/USER_GUIDES/CONFIGURATION.md)
- Check [API Reference](../../docs/REFERENCES/API_REFERENCE.md)
- Join our [Discord](https://discord.gg/xcW8c7fF3R)
