# Automagik Telemetry Examples

This directory contains practical examples for using the Automagik Telemetry SDKs in Python and TypeScript.

## Quick Start

### Python Examples

```bash
cd python
pip install -r requirements.txt
python basic_example.py
```

### TypeScript Examples

```bash
cd typescript
npm install
npm run basic
```

## Available Examples

### Python

- **`basic_example.py`** - Simple getting started example showing events, metrics, and logs
- **`omni_example.py`** - Real-world integration with Omni messaging system
- **`test_opt_in.py`** - Testing opt-in/opt-out functionality

### TypeScript

- **`basic_example.ts`** - Simple getting started example showing events, metrics, and logs
- **`forge_example.ts`** - Real-world integration with Forge task management
- **`tools_example.ts`** - Advanced usage with MCP tools integration

## Local Infrastructure Setup

All examples can be tested against local infrastructure for development and testing:

```bash
# Start all services (ClickHouse, OTLP Collector, Grafana)
cd infra
make start

# Check health
make health

# View in Grafana
open http://localhost:3000
# Default credentials: admin/admin

# Stop services
make stop
```

## Services

When running local infrastructure, the following services are available:

- **Grafana**: http://localhost:3000 - Visualization dashboards
- **OTLP Collector**: http://localhost:4318 - Telemetry data ingestion
- **ClickHouse**: http://localhost:8123 - Data storage
- **Health Check**: http://localhost:13133 - Collector health status

## Configuration

Both SDKs support configuration via environment variables:

```bash
# Enable telemetry
export AUTOMAGIK_TELEMETRY_ENABLED=true

# Set local endpoint
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces

# Enable debug logging
export AUTOMAGIK_TELEMETRY_VERBOSE=true

# Configure project info
export AUTOMAGIK_TELEMETRY_PROJECT_NAME=my-app
export AUTOMAGIK_TELEMETRY_PROJECT_VERSION=1.0.0

# Choose backend
export AUTOMAGIK_TELEMETRY_BACKEND=otlp  # or "clickhouse"
```

## Directory Structure

```
examples/
├── README.md              # This file
├── python/                # Python SDK examples
│   ├── README.md          # Python-specific documentation
│   ├── requirements.txt   # Python dependencies
│   ├── basic_example.py   # Simple usage
│   ├── omni_example.py    # Omni integration
│   └── test_opt_in.py     # Opt-in testing
└── typescript/            # TypeScript SDK examples
    ├── README.md          # TypeScript-specific documentation
    ├── package.json       # TypeScript dependencies
    ├── basic_example.ts   # Simple usage
    ├── forge_example.ts   # Forge integration
    └── tools_example.ts   # MCP tools usage
```

## Example Workflow

1. **Start with basic examples** to understand core concepts
2. **Review real-world examples** (omni/forge/tools) for integration patterns
3. **Test locally** using the infrastructure setup
4. **Configure for production** with your own endpoints
5. **Monitor in Grafana** to verify data flow

## Common Tasks

### Testing Privacy Features

```python
# Python
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig

config = TelemetryConfig(
    project_name="privacy-test",
    version="1.0.0",
)
telemetry = AutomagikTelemetry(config=config)

# This data will be sanitized automatically
telemetry.track_event("user.action", {
    "email": "user@example.com",  # Will be redacted
    "api_key": "sk_test_123",     # Will be redacted
    "safe_data": "public info",   # Will be kept
})
```

```typescript
// TypeScript
import { AutomagikTelemetry } from 'automagik-telemetry';

const telemetry = new AutomagikTelemetry({
  projectName: 'privacy-test',
  projectVersion: '1.0.0',
});

// This data will be sanitized automatically
telemetry.trackEvent('user.action', {
  email: 'user@example.com',  // Will be redacted
  api_key: 'sk_test_123',     // Will be redacted
  safe_data: 'public info',   // Will be kept
});
```

### Using ClickHouse Backend

```bash
# Set backend to ClickHouse
export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://localhost:8123

# Run examples
python python/basic_example.py
# or
npm --prefix typescript run basic
```

### Opting Out

```bash
# Create opt-out file to disable telemetry
touch ~/.automagik-no-telemetry

# Verify telemetry is disabled
python python/test_opt_in.py

# Re-enable
rm ~/.automagik-no-telemetry
```

## Troubleshooting

### No data appearing in Grafana

1. Check services are running: `cd infra && make health`
2. Enable verbose mode: `export AUTOMAGIK_TELEMETRY_VERBOSE=true`
3. Check telemetry is enabled: Remove `~/.automagik-no-telemetry`
4. Verify endpoint is correct: `http://localhost:4318/v1/traces`

### Connection errors

1. Ensure infrastructure is started: `cd infra && make start`
2. Check ports are not blocked by firewall
3. Verify Docker containers are running: `docker ps`

### Import/Module errors

**Python:**
```bash
pip install -r python/requirements.txt
# or install from source
pip install -e python/
```

**TypeScript:**
```bash
cd typescript
npm install
```

## Next Steps

- Read the [Getting Started Guide](../docs/GETTING_STARTED.md)
- Explore [API Reference](../docs/REFERENCES/API_REFERENCE.md)
- Learn about [Configuration Options](../docs/USER_GUIDES/CONFIGURATION.md)
- Understand [Privacy Features](../docs/USER_GUIDES/PRIVACY.md)
- Set up [Self-Hosting](../docs/USER_GUIDES/SELF_HOSTING.md)

## Support

- **Documentation**: https://github.com/namastexlabs/automagik-telemetry/tree/main/docs
- **Discord**: https://discord.gg/xcW8c7fF3R
- **Issues**: https://github.com/namastexlabs/automagik-telemetry/issues
