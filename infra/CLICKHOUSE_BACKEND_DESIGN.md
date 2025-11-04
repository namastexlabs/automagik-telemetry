# ClickHouse Direct Backend Design Document

📚 User guide available at [docs/USER_GUIDES/BACKENDS.md](../docs/USER_GUIDES/BACKENDS.md)

This is a technical design document. For user-facing configuration and usage instructions, see the Backend Configuration Guide above.

## Problem Statement

### The Bug We Encountered

The OpenTelemetry Collector's ClickHouse exporter fails with:
```
exec create traceID timestamp view sql: [HTTP 404] failed to read response:
read next block: data size should be 0 < 540700271 < 134217728
```

**Root cause**: When the exporter queries ClickHouse system tables during startup, it receives a 540MB response that exceeds the 128MB protocol limit, causing a fatal error.

### Why We Can't Use the Standard Exporter

The fundamental issue is **architectural incompatibility**:

| Our Requirements | OTLP Exporter Design |
|------------------|---------------------|
| Custom schema with fields like `project_name`, `span_name` | Auto-generates opinionated `otel_traces` schema |
| Pre-defined tables via `init-db.sql` | Expects to own all DDL |
| Flexible attribute mapping | Rigid, standard OTLP fields only |
| Custom indexes and partitioning | One-size-fits-all approach |

**Conclusion**: The exporter is designed for users who want OpenTelemetry's standard schema. We need our own schema for our specific use case.

---

## Solution: Direct ClickHouse Backend

### Architecture

Instead of using the problematic middleware, we bypass it:

```
BEFORE (Broken):
SDK → OTLP Protocol → Collector → ClickHouse Exporter 💥 → ClickHouse

AFTER (Working):
SDK → ClickHouse Backend → ClickHouse HTTP API ✅ → ClickHouse
```

### Why This Approach?

**Options considered:**

1. **Fix the OTLP exporter** ❌
   - Not our code (upstream dependency)
   - Would need community contribution, review, release cycle
   - Design mismatch would remain
   - Timeline: Weeks to months

2. **Use Vector collector** ❌
   - Different tool, migration effort
   - Another dependency to manage
   - Learning curve

3. **File-based insertion** ❌
   - Not real-time
   - Complex batch processing
   - Additional cron jobs needed

4. **Direct SDK → ClickHouse** ✅ **SELECTED**
   - **Simplest**: Fewest components
   - **Fastest**: Implemented in hours
   - **Full control**: We own the transformation
   - **No deps**: Uses stdlib only
   - **Reliable**: No middleware bugs

---

## Implementation Details

### Component Overview

We created **backend modules** for both SDKs:

```
python/src/automagik_telemetry/backends/
├── __init__.py
└── clickhouse.py          # Python implementation

typescript/src/backends/
├── index.ts
└── clickhouse.ts          # TypeScript implementation
```

### Data Flow

```
1. SDK generates OTLP-formatted span
   ↓
2. ClickHouseBackend.transform_otlp_to_clickhouse()
   → Flattens nested OTLP structure
   → Maps to our ClickHouse schema
   → Returns flat dictionary
   ↓
3. ClickHouseBackend.add_to_batch()
   → Queues row for insertion
   → Auto-flushes when batch size reached
   ↓
4. ClickHouseBackend.flush()
   → Converts batch to JSONEachRow format
   → Compresses if > 1KB
   → POSTs to ClickHouse HTTP API
   ↓
5. ClickHouse inserts row into traces table
```

### Schema Transformation

**Input: OTLP Format**
```json
{
  "traceId": "abc123",
  "spanId": "def456",
  "name": "user.login",
  "startTimeUnixNano": 1729627200000000000,
  "endTimeUnixNano": 1729627200145000000,
  "attributes": [
    {"key": "user.id", "value": {"stringValue": "123"}}
  ],
  "resource": {
    "attributes": [
      {"key": "service.name", "value": {"stringValue": "my-app"}},
      {"key": "project.name", "value": {"stringValue": "my-app"}}
    ]
  },
  "status": {"code": 1}
}
```

**Output: ClickHouse Row**
```json
{
  "trace_id": "abc123",
  "span_id": "def456",
  "span_name": "user.login",
  "timestamp": "2025-10-22 20:00:00",
  "timestamp_ns": 1729627200000000000,
  "duration_ms": 145,
  "service_name": "my-app",
  "project_name": "my-app",
  "status_code": "OK",
  "attributes": {"user.id": "123"}
}
```

**Transformation steps:**
1. Flatten nested structure to flat dict
2. Convert nanosecond timestamps to DateTime
3. Calculate duration from start/end times
4. Extract resource attributes to top-level fields
5. Transform attributes array to Map(String, String)
6. Map OTLP status codes to our status_code field

### Key Features

#### 1. Batch Processing
- **Why**: Reduces HTTP overhead (100 requests → 1 request)
- **How**: Queue rows until batch size reached
- **Default**: 100 rows per batch
- **Configurable**: `batch_size` parameter

#### 2. Compression
- **Why**: Reduces network bandwidth by ~70-90%
- **How**: Gzip compression via stdlib
- **Threshold**: Only compress if payload > 1KB
- **Configurable**: `compression_enabled` and `compression_threshold`

#### 3. Retry Logic
- **Why**: Handle transient network failures
- **How**: Exponential backoff (1s, 2s, 4s)
- **Default**: 3 retry attempts
- **Configurable**: `max_retries` parameter

#### 4. Error Handling
- **Philosophy**: Silent failures - log errors but never crash the app
- **Why**: Telemetry should never break the application
- **How**: Try/except blocks with logging

#### 5. Zero Dependencies
- **Python**: Uses only `urllib`, `json`, `gzip`, `time` (stdlib)
- **TypeScript**: Uses only `http`, `https`, `zlib` (stdlib)
- **Why**: Keeps SDK lightweight, no version conflicts, easier to audit

---

## Usage (Future - After Integration)

### Python Example
```python
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig

# Use ClickHouse backend for local dev
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    backend="clickhouse",  # Instead of default "otlp"
    clickhouse_endpoint="http://localhost:8123",
    clickhouse_database="telemetry",
    batch_size=100
)
client = AutomagikTelemetry(config=config)

client.track_event("user.login", {"user_id": "123"})
# → Goes directly to ClickHouse
```

### TypeScript Example
```typescript
import { AutomagikTelemetry } from 'automagik-telemetry';

// Use ClickHouse backend for local dev
const client = new AutomagikTelemetry({
  projectName: 'my-app',
  version: '1.0.0',
  backend: 'clickhouse',  // Instead of default 'otlp'
  clickhouseEndpoint: 'http://localhost:8123',
  clickhouseDatabase: 'telemetry',
  batchSize: 100
});

client.trackEvent('user.login', { userId: '123' });
// → Goes directly to ClickHouse
```

### Environment Variables
```bash
# Local development with ClickHouse
export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://localhost:8123

# Production with OTLP
export AUTOMAGIK_TELEMETRY_BACKEND=otlp
export AUTOMAGIK_TELEMETRY_ENDPOINT=https://telemetry.namastex.ai/v1/traces
```

---

## Configuration Options

### ClickHouseBackend Constructor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `endpoint` | string | `http://localhost:8123` | ClickHouse HTTP API endpoint |
| `database` | string | `telemetry` | Database name |
| `table` | string | `traces` | Table name for traces |
| `username` | string | `default` | ClickHouse username |
| `password` | string | `` | ClickHouse password |
| `timeout` | int | `5` (seconds) | HTTP timeout |
| `batch_size` | int | `100` | Rows to batch before insert |
| `compression_enabled` | bool | `true` | Enable gzip compression |
| `max_retries` | int | `3` | Maximum retry attempts |

---

## Performance Characteristics

### Benchmarks (Estimated)

| Metric | Without Batching | With Batching (100 rows) |
|--------|------------------|--------------------------|
| HTTP Requests | 1000 | 10 |
| Network Overhead | ~100KB | ~10KB |
| Latency | ~1000ms | ~100ms |
| Compression Ratio | 1x | ~10x (with gzip) |

### Memory Usage
- **Bounded by batch size**: Max memory = batch_size × avg_row_size
- **Example**: 100 rows × 1KB/row = ~100KB maximum
- **After flush**: Memory released immediately

### Network Usage
- **Without compression**: ~1KB per row
- **With compression**: ~100-200 bytes per row (70-90% reduction)
- **Batch mode**: Single HTTP request per 100 rows

---

## Testing Strategy

### Unit Tests
```python
def test_otlp_to_clickhouse_transformation():
    """Verify OTLP → ClickHouse mapping is correct"""
    backend = ClickHouseBackend()
    otlp_span = {...}  # Sample OTLP data
    row = backend.transform_otlp_to_clickhouse(otlp_span)
    assert row["trace_id"] == otlp_span["traceId"]
    assert row["span_name"] == otlp_span["name"]
    # ... etc

def test_batch_auto_flush():
    """Verify batch auto-flushes at batch_size"""
    backend = ClickHouseBackend(batch_size=10)
    for i in range(9):
        backend.add_to_batch(otlp_span)
    assert len(backend._batch) == 9
    backend.add_to_batch(otlp_span)  # Should trigger flush
    assert len(backend._batch) == 0

def test_compression():
    """Verify compression activates for large payloads"""
    backend = ClickHouseBackend(compression_threshold=1024)
    # Test with small payload
    # Test with large payload
    # Verify gzip header present
```

### Integration Tests
```bash
# Start local ClickHouse
cd infra && make start

# Run Python SDK test
cd python
python -c "
from automagik_telemetry.backends import ClickHouseBackend
backend = ClickHouseBackend()
backend.send_trace({...otlp_span...})
backend.flush()
"

# Verify in ClickHouse
docker exec automagik-clickhouse clickhouse-client --query="
SELECT count() FROM telemetry.traces
"
# Should return: 1

# Verify in Grafana
curl http://localhost:3000/api/datasources/proxy/1/...
```

---

## Migration Path

### Phase 1: Backend Modules (✅ Complete)
- [x] Implement `ClickHouseBackend` class (Python)
- [x] Implement `ClickHouseBackend` class (TypeScript)
- [x] Add to version control
- [x] Document design decisions

### Phase 2: Integration (In Progress)
- [ ] Update `AutomagikTelemetry` class to accept `backend` parameter
- [ ] Add backend selection logic
- [ ] Add ClickHouse-specific config options
- [ ] Update config validation

### Phase 3: Testing (Pending)
- [ ] Unit tests for transformation logic
- [ ] Unit tests for batch processing
- [ ] Integration test: Python SDK → ClickHouse
- [ ] Integration test: TypeScript SDK → ClickHouse
- [ ] Verify data in Grafana dashboards

### Phase 4: Documentation (Pending)
- [ ] Update README with ClickHouse backend examples
- [ ] Update infra/README.md with architecture
- [ ] Create migration guide for users
- [ ] Add configuration reference

### Phase 5: Rollout (Future)
- [ ] Release as experimental feature
- [ ] Gather feedback from self-hosting users
- [ ] Promote to stable once validated

---

## Future Enhancements

### Possible Improvements

1. **Metrics Backend**
   - Add `ClickHouseMetricsBackend` for metrics data
   - Separate table for efficient metrics storage

2. **Logs Backend**
   - Add `ClickHouseLogsBackend` for logs data
   - Optimized schema for log aggregation

3. **Async Insertion**
   - Use ClickHouse's async insert mode
   - Further reduces latency

4. **Connection Pooling**
   - Reuse HTTP connections
   - Reduces connection overhead

5. **Schema Evolution**
   - Version the schema
   - Handle migrations gracefully

---

## Alternatives Considered

### Why Not Keep Fighting with OTLP Exporter?

**Effort required to fix:**
1. Debug the exact cause of 540MB response
2. Fork `opentelemetry-collector-contrib`
3. Implement fix (likely complex)
4. Write tests
5. Submit PR to upstream
6. Wait for review (could be weeks)
7. Wait for next release (could be months)
8. Update our dependencies
9. **Still have design mismatch with schema ownership**

**Effort for direct backend:**
1. Write transformation logic (2 hours)
2. Write HTTP insertion logic (1 hour)
3. Test (1 hour)
4. **Done, with full control**

### Why Not Use a Different Collector?

**Vector** is excellent but:
- Adds another tool to learn
- Migration effort for existing OTLP setup
- Another dependency to manage
- Doesn't fundamentally solve "we want custom schema"

**Our approach**:
- Leverages existing SDK architecture
- Minimal new code
- Full control over data flow
- Works alongside OTLP for production

---

## Security Considerations

### Data in Transit
- Uses HTTP (not HTTPS) by default for local dev
- **Production**: Should use HTTPS with valid certificates
- Supports HTTP Basic Auth for authenticated ClickHouse

### Data at Rest
- ClickHouse handles encryption at rest
- Our backend doesn't store data (passes through)

### PII Handling
- No change from current approach
- Still relies on SDK-level sanitization
- Backend just transforms and forwards

---

## Monitoring & Observability

### Logging
Both backends log:
- Successful insertions (debug level)
- HTTP errors (error level)
- Network timeouts (error level)
- Retry attempts (warning level)

### Metrics (Future)
Could add:
- Batch sizes over time
- Insertion success/failure rates
- Latency percentiles
- Compression ratios

### Debugging
- Logs show exact HTTP requests being made
- Can inspect batch contents before sending
- ClickHouse query logs show incoming data

---

## FAQ

### Q: Why not just fix the ClickHouse exporter?
**A**: It's not our code, fixing it properly would take weeks/months, and even then it has a design mismatch with our custom schema requirements.

### Q: Does this mean we're abandoning OTLP?
**A**: No! OTLP remains the default for production. This is an *additional* backend option for local dev and self-hosting.

### Q: What if ClickHouse is down?
**A**: The backend will log errors and fail silently (as telemetry should). Your app continues running normally.

### Q: Can we switch backends at runtime?
**A**: Not currently. Backend is chosen at client initialization. Could add hot-swapping in the future if needed.

### Q: What about backwards compatibility?
**A**: Fully backwards compatible. Existing OTLP usage is unchanged. ClickHouse backend is opt-in.

### Q: Performance impact?
**A**: Minimal. Batching reduces HTTP overhead. Compression reduces network usage. Overall likely faster than going through collector middleware.

---

## Conclusion

The direct ClickHouse backend solves our immediate blocker (broken OTLP exporter) while giving us:

✅ **Simplicity** - Fewer moving parts
✅ **Control** - We own the data flow
✅ **Reliability** - No middleware bugs
✅ **Performance** - Direct insertion is faster
✅ **Maintainability** - Pure stdlib, easy to understand

This approach aligns with our principle of **simple, reliable infrastructure** over complex middleware that we don't control.
