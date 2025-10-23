# Automagik Telemetry - TypeScript SDK

> **📚 [Complete Documentation](../docs/INDEX.md)** | **🚀 [Main README](../README.md)** | **⚙️ [Configuration Guide](../docs/USER_GUIDES/CONFIGURATION.md)**

Privacy-first OpenTelemetry SDK for TypeScript/JavaScript applications with zero dependencies and 100% test coverage.

## Installation

```bash
npm install @automagik/telemetry
# or
pnpm add @automagik/telemetry
```

**Requirements:** Node.js 18+

## Quick Start

```typescript
import { AutomagikTelemetry, MetricType } from '@automagik/telemetry';

// Initialize client
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Track events (traces)
client.trackEvent('user.login', {
    userId: 'anonymous-123',
    method: 'oauth'
});

// Track metrics (counter, gauge, histogram)
client.trackMetric('api.requests', 1, MetricType.COUNTER, {
    endpoint: '/api/users',
    status: 200
});
```

## Key Configuration

### Batch Size (Default: `batchSize=100`)

```typescript
// Default: Batch 100 events (optimized for performance)
const client = new AutomagikTelemetry({ projectName: 'my-app', version: '1.0.0' });

// Disable batching for real-time apps
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    batchSize: 1  // Send immediately
});
```

### Backend Selection

```typescript
// OTLP Backend (default - production)
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    endpoint: 'https://telemetry.namastex.ai'
});

// ClickHouse Backend (self-hosting)
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    backend: 'clickhouse',
    clickhouseEndpoint: 'http://localhost:8123'
});
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

### Graceful Shutdown

```typescript
// Ensure all telemetry is sent before app exits
process.on('SIGTERM', async () => {
    await client.shutdown();  // Flushes pending events
    process.exit(0);
});
```

## Development

```bash
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

## Documentation

- **[Getting Started](../docs/GETTING_STARTED.md)** - Complete setup guide
- **[Configuration](../docs/USER_GUIDES/CONFIGURATION.md)** - All configuration options
- **[Backends Guide](../docs/USER_GUIDES/BACKENDS.md)** - OTLP vs ClickHouse comparison
- **[API Reference](../docs/REFERENCES/API_REFERENCE.md)** - Complete API documentation
- **[SDK Differences](../docs/DEVELOPER_GUIDES/SDK_DIFFERENCES.md)** - Python vs TypeScript
- **[Troubleshooting](../docs/REFERENCES/TROUBLESHOOTING.md)** - Common issues and solutions

## TypeScript-Specific Features

- **Fire-and-forget async:** All methods return void but handle async internally
- **camelCase naming:** Follows JavaScript conventions (`trackEvent`, `projectName`)
- **Strict TypeScript:** Full type safety with strict mode enabled
- **Time units:** `flushInterval` in milliseconds (number)

See [SDK Differences](../docs/DEVELOPER_GUIDES/SDK_DIFFERENCES.md) for Python vs TypeScript comparison.

## License

MIT - see [LICENSE](../LICENSE) for details.
