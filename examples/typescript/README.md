# TypeScript Examples

This directory contains examples demonstrating how to use the Automagik Telemetry TypeScript SDK.

## Prerequisites

```bash
# Install dependencies
npm install
# or
pnpm install

# The SDK will be installed from npm
# To use local development version:
cd ../../typescript
pnpm link
cd ../examples/typescript
pnpm link automagik-telemetry
```

## Running Examples

### Basic Example

The simplest way to get started. Shows event tracking, metrics, and logs.

```bash
npm run basic
# or
tsx basic_example.ts
```

### Forge Example

Real-world example showing integration with Forge task management.

```bash
npm run forge
# or
tsx forge_example.ts
```

### Tools Example

Advanced example showing MCP tools integration.

```bash
npm run tools
# or
tsx tools_example.ts
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
cd ../examples/typescript

# Set environment variables for local testing
export AUTOMAGIK_TELEMETRY_ENABLED=true
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces
export AUTOMAGIK_TELEMETRY_VERBOSE=true

npm run basic

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

```typescript
import { AutomagikTelemetry } from 'automagik-telemetry';

const telemetry = new AutomagikTelemetry({
  projectName: 'my-project',
  projectVersion: '1.0.0',
  endpoint: 'http://localhost:4318/v1/traces',
  backend: 'otlp',  // or 'clickhouse'
  batchSize: 100,
  flushInterval: 5000,  // milliseconds
  timeout: 5,  // seconds
  verbose: true,
});
```

## Example Structure

```
examples/typescript/
├── README.md              # This file
├── package.json           # Dependencies and scripts
├── basic_example.ts       # Simple getting started example
├── forge_example.ts       # Real-world Forge integration
└── tools_example.ts       # Advanced MCP tools usage
```

## Troubleshooting

### Telemetry not sending data

1. Check if telemetry is enabled:
   ```typescript
   const status = telemetry.getStatus();
   console.log(status.enabled);
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

### Module not found errors

1. Ensure dependencies are installed:
   ```bash
   npm install
   # or
   pnpm install
   ```

2. Check Node.js version:
   ```bash
   node --version  # Should be >= 18.0.0
   ```

3. Reinstall if needed:
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

### TypeScript errors

1. Install tsx if not present:
   ```bash
   npm install -g tsx
   ```

2. Alternative: use ts-node:
   ```bash
   npm install -g ts-node
   ts-node basic_example.ts
   ```

## Next Steps

- Read the [Getting Started Guide](../../docs/GETTING_STARTED.md)
- Explore [Configuration Options](../../docs/USER_GUIDES/CONFIGURATION.md)
- Check [API Reference](../../docs/REFERENCES/API_REFERENCE.md)
- Join our [Discord](https://discord.gg/xcW8c7fF3R)
