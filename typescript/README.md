# Automagik Telemetry - TypeScript SDK

Privacy-first OpenTelemetry SDK for TypeScript/JavaScript applications.

## Installation

```bash
npm install @automagik/telemetry
# or
pnpm add @automagik/telemetry
```

## Quick Start

```typescript
import { AutomagikTelemetry, MetricType } from '@automagik/telemetry';

// Initialize client
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Track events
client.trackEvent('user.login', {
    userId: 'anonymous-123',
    method: 'oauth'
});

// Track metrics
client.trackMetric('api.requests', 1, MetricType.COUNTER, {
    endpoint: '/api/users',
    status: 200
});
```

## Documentation

Full documentation: [github.com/namastexlabs/automagik-telemetry](https://github.com/namastexlabs/automagik-telemetry)

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
```

## License

MIT - see [LICENSE](../LICENSE) for details.
