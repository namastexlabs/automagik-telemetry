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

## Configuration

### Batch Size

The TypeScript SDK defaults to `batchSize=100`, which batches events before sending them to the telemetry backend. This provides efficient network usage and better performance for most applications.

**Enable immediate sending:**

```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    batchSize: 1  // Send events immediately
});
```

**When to use batching (default):**
- Most production applications
- High-volume event streams
- Optimizing network usage

**When to use immediate send (batchSize=1):**
- Critical real-time events
- Low-latency requirements
- Debugging and testing

> **Note:** The Python SDK defaults to `batch_size=1` for immediate sending. See [main README](https://github.com/namastexlabs/automagik-telemetry#configuration) for cross-SDK differences.

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
