# Coding Conventions

This document explains the coding conventions, naming patterns, and design decisions used across the Automagik Telemetry SDKs.

## Language-Specific Conventions

### Python SDK

**Style Guide:** Follows [PEP 8](https://peps.python.org/pep-0008/) - Python Enhancement Proposal 8

**Naming Conventions:**
- **Functions/Methods:** `snake_case`
  - `track_event()`, `track_metric()`, `flush()`
- **Classes:** `PascalCase`
  - `AutomagikTelemetry`, `TelemetryConfig`, `MetricType`
- **Constants:** `UPPER_SNAKE_CASE`
  - `DEFAULT_ENDPOINT`, `MAX_RETRIES`
- **Variables/Parameters:** `snake_case`
  - `project_name`, `batch_size`, `flush_interval`
- **Private Methods:** Prefixed with `_`
  - `_send_event()`, `_compress_payload()`

**Type Hints:**
- Required for all public methods
- Uses Python 3.12+ syntax (`str | None` instead of `Optional[str]`)

**Example:**
```python
def track_metric(
    self,
    metric_name: str,
    value: float,
    metric_type: MetricType = MetricType.GAUGE,
    attributes: dict[str, Any] | None = None
) -> None:
    pass
```

### TypeScript SDK

**Style Guide:** Follows [TypeScript/JavaScript conventions](https://google.github.io/styleguide/tsguide.html)

**Naming Conventions:**
- **Functions/Methods:** `camelCase`
  - `trackEvent()`, `trackMetric()`, `flush()`
- **Classes:** `PascalCase`
  - `AutomagikTelemetry`, `TelemetryConfig`
- **Interfaces:** `PascalCase`
  - `TelemetryConfig`, `OTLPAttribute`
- **Constants:** `UPPER_SNAKE_CASE` or `camelCase`
  - `DEFAULT_ENDPOINT` or `defaultEndpoint`
- **Variables/Parameters:** `camelCase`
  - `projectName`, `batchSize`, `flushInterval`
- **Private Properties:** Prefixed with `private`
  - `private sendEvent()`, `private compressPayload()`

**Type Annotations:**
- Required for all public methods
- Uses TypeScript interfaces for configuration

**Example:**
```typescript
trackMetric(
    metricName: string,
    value: number,
    metricType: 'counter' | 'gauge' | 'histogram' = 'gauge',
    attributes?: Record<string, any>
): void {
    // ...
}
```

## Cross-SDK API Consistency

Despite language-specific naming conventions, the APIs are functionally identical:

| Concept | Python | TypeScript |
|---------|--------|------------|
| Main Class | `AutomagikTelemetry` | `AutomagikTelemetry` |
| Track Event | `track_event()` | `trackEvent()` |
| Track Metric | `track_metric()` | `trackMetric()` |
| Track Error | `track_error()` | `trackError()` |
| Track Log | `track_log()` | `trackLog()` |
| Flush Events | `flush()` | `flush()` |
| Shutdown | `shutdown()` | `shutdown()` |

### Configuration Parameters

| Parameter | Python | TypeScript |
|-----------|--------|------------|
| Project Name | `project_name` | `projectName` |
| Version | `version` | `version` |
| Backend | `backend` | `backend` |
| Endpoint | `endpoint` | `endpoint` |
| Batch Size | `batch_size` | `batchSize` |
| Flush Interval | `flush_interval` | `flushInterval` |
| Compression Enabled | `compression_enabled` | `compressionEnabled` |
| Max Retries | `max_retries` | `maxRetries` |

## Configuration Defaults

### Intentional Differences

Some defaults differ between SDKs for good reasons:

| Setting | Python Default | TypeScript Default | Reason |
|---------|---------------|-------------------|---------|
| **Batch Size** | `1` | `100` | Python optimized for debugging/simplicity; TypeScript for performance |
| **Flush Interval** | `5.0` (seconds) | `5000` (milliseconds) | Language convention (Python uses seconds, JS uses ms) |

### Shared Defaults

These defaults are identical across both SDKs:

| Setting | Default Value | Reason |
|---------|--------------|---------|
| **Backend** | `"otlp"` | Standard OpenTelemetry protocol |
| **Endpoint** | `"https://telemetry.namastex.ai"` | Automagik's hosted telemetry service |
| **Organization** | `"namastex"` | Default organization identifier |
| **Timeout** | `5` (seconds in both) | Reasonable HTTP timeout |
| **Compression Enabled** | `true` | Reduce bandwidth usage |
| **Compression Threshold** | `1024` (bytes) | Only compress payloads >1KB |
| **Max Retries** | `3` | Balance reliability vs responsiveness |

## Environment Variables

Both SDKs check the same environment variables:

| Variable | Purpose | Values |
|----------|---------|--------|
| `AUTOMAGIK_TELEMETRY_DISABLED` | Disable telemetry | `"true"` / `"false"` |
| `AUTOMAGIK_TELEMETRY_ENDPOINT` | Override default endpoint | URL string |
| `ENVIRONMENT` | Auto-disable in dev | `"development"` disables telemetry |

## Metric Types

Both SDKs support the same OTLP metric types:

| Type | Python | TypeScript | Use Case |
|------|--------|------------|----------|
| **Counter** | `MetricType.COUNTER` or `"counter"` | `'counter'` | Monotonically increasing values (requests, errors) |
| **Gauge** | `MetricType.GAUGE` or `"gauge"` | `'gauge'` | Point-in-time values (CPU%, memory, queue size) |
| **Histogram** | `MetricType.HISTOGRAM` or `"histogram"` | `'histogram'` | Distribution of values (latency, request size) |

## Error Handling

### Python
```python
# Telemetry errors are logged but never throw exceptions
# This ensures telemetry failures don't break your application
try:
    self._send_event(...)
except Exception as e:
    logger.error(f"Telemetry error: {e}")
    # Application continues normally
```

### TypeScript
```typescript
// Telemetry errors are caught and logged silently
// Application flow is never interrupted
try {
    this.sendEvent(...);
} catch (error) {
    console.error('Telemetry error:', error);
    // Application continues normally
}
```

## Code Style

### Python
- **Formatter:** `ruff format`
- **Linter:** `ruff check`
- **Type Checker:** `mypy` (strict mode)
- **Line Length:** 100 characters
- **Imports:** Sorted by `ruff` (stdlib, third-party, local)

### TypeScript
- **Formatter:** `prettier`
- **Linter:** `eslint` with TypeScript plugin
- **Type Checker:** `tsc` (strict mode)
- **Line Length:** 100 characters (Prettier default)

## Testing Conventions

### Python
- **Framework:** `pytest`
- **Coverage:** 100% required (`pytest-cov`)
- **Test File Naming:** `test_*.py`
- **Async Tests:** `pytest-asyncio`

### TypeScript
- **Framework:** `jest`
- **Coverage:** 100% required
- **Test File Naming:** `*.test.ts`
- **Integration Tests:** `*.integration.test.ts`

## Documentation

### Docstrings (Python)
```python
def track_event(self, event_name: str, attributes: dict[str, Any] | None = None) -> None:
    """
    Track an event using OTLP traces format.

    Args:
        event_name: Name of the event to track
        attributes: Optional event attributes

    Example:
        >>> telemetry.track_event("user.login", {"method": "oauth"})
    """
```

### JSDoc (TypeScript)
```typescript
/**
 * Track an event using OTLP traces format.
 *
 * @param eventName - Name of the event to track
 * @param attributes - Optional event attributes
 *
 * @example
 * telemetry.trackEvent('user.login', { method: 'oauth' });
 */
trackEvent(eventName: string, attributes?: Record<string, any>): void {
```

## Privacy Conventions

Both SDKs follow these privacy-first principles:

1. **Opt-in by Default:** Disabled in development environments
2. **No PII Collection:** Never collect personally identifiable information
3. **Anonymous Metrics:** Use anonymous identifiers only
4. **Easy Opt-out:** Single environment variable to disable
5. **Transparent:** All collected data documented

## Version Compatibility

### Python
- **Minimum Version:** Python 3.12+
- **Reason:** Uses modern type hint syntax (`str | None`)

### TypeScript
- **Minimum Version:** Node.js 18+
- **TypeScript:** 5.4+
- **Reason:** Uses modern ES modules and async patterns

---

## Contributing

When contributing to either SDK, ensure you:

1. Follow the language-specific style guide
2. Maintain 100% test coverage
3. Add type hints/annotations
4. Include docstrings/JSDoc
5. Keep APIs consistent between SDKs
6. Update both SDKs when adding features
7. Run linters and formatters before committing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.
