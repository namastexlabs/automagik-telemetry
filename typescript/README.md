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

## Async Usage

All tracking methods in TypeScript are internally async but designed for fire-and-forget usage:

### Standard Usage (Fire-and-Forget)
```typescript
// Methods return void and handle async internally
client.trackEvent('user.login', { userId: 'anonymous-123' });
client.trackMetric('api.requests', 1, { status: 200 });

// No need to await - telemetry is sent asynchronously in the background
```

### Ensuring Delivery Before Shutdown
```typescript
// If you need to ensure all telemetry is sent before your app exits
process.on('SIGTERM', async () => {
    await client.shutdown();  // Flushes all pending events
    process.exit(0);
});
```

### Integration with Async Functions
```typescript
async function handleRequest() {
    try {
        const result = await processUserRequest();

        // Track success (fire-and-forget)
        client.trackEvent('request.success', {
            duration: result.duration
        });

        return result;
    } catch (error) {
        // Track error (fire-and-forget)
        client.trackError(error as Error, {
            endpoint: '/api/users'
        });
        throw error;
    }
}
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

## 📚 Documentation

**Complete documentation:** [Documentation Index](../docs/INDEX.md)

**Quick Links:**
- 🚀 [Getting Started Guide](../docs/GETTING_STARTED.md)
- ⚙️ [Configuration Reference](../docs/USER_GUIDES/CONFIGURATION.md)
- 📊 [Backends Guide (OTLP vs ClickHouse)](../docs/USER_GUIDES/BACKENDS.md)
- 🔍 [API Reference](../docs/REFERENCES/API_REFERENCE.md)
- 🐛 [Troubleshooting](../docs/REFERENCES/TROUBLESHOOTING.md)
- 🔧 [SDK Differences (Python ↔ TypeScript)](../docs/DEVELOPER_GUIDES/SDK_DIFFERENCES.md)

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

## 🔗 Related Documentation

- **[Implementation Guide](../docs/DEVELOPER_GUIDES/IMPLEMENTATION.md)** - Integration patterns
- **[Testing Guide](../docs/DEVELOPER_GUIDES/TESTING.md)** - Test strategies
- **[Architecture](../docs/DEVELOPER_GUIDES/ARCHITECTURE.md)** - System design
- **[Contributing](../docs/DEVELOPER_GUIDES/CONTRIBUTING.md)** - Development workflow

## License

MIT - see [LICENSE](../LICENSE) for details.
