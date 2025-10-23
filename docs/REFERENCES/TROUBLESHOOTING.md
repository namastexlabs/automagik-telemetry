# Troubleshooting Guide

> **🔍 Quick solutions** for common Automagik Telemetry issues. Scannable format with diagnostic commands and copy-paste fixes.

---

## 📖 Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Common Issues](#common-issues)
- [Error Codes](#error-codes)
- [Backend-Specific Issues](#backend-specific-issues)
- [Performance Issues](#performance-issues)
- [Debugging Tools](#debugging-tools)

---

## Quick Diagnostics

### ⚡ One-Liner Health Check

<details>
<summary><strong>Python - Quick Status Check</strong></summary>

```python
from automagik_telemetry import AutomagikTelemetry

telemetry = AutomagikTelemetry(project_name="test", version="1.0.0")
print(telemetry.get_status())
```

**Expected Output:**
```python
{
    'enabled': True,  # Should be True if properly configured
    'user_id': 'uuid-...',
    'session_id': 'uuid-...',
    'endpoint': 'https://telemetry.namastex.ai/v1/traces',
    'batch_size': 1,
    'queue_sizes': {'traces': 0, 'metrics': 0, 'logs': 0}
}
```
</details>

<details>
<summary><strong>TypeScript - Quick Status Check</strong></summary>

```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const telemetry = new AutomagikTelemetry({ projectName: 'test', version: '1.0.0' });
console.log(telemetry.getStatus());
```

**Expected Output:**
```typescript
{
    enabled: true,  // Should be true if properly configured
    userId: 'uuid-...',
    sessionId: 'uuid-...',
    endpoint: 'https://telemetry.namastex.ai/v1/traces',
    batchSize: 100
}
```
</details>

---

### 🔍 Environment Check

```bash
# Run this in your terminal
echo "=== Telemetry Configuration ==="
echo "Enabled: ${AUTOMAGIK_TELEMETRY_ENABLED:-not set}"
echo "Backend: ${AUTOMAGIK_TELEMETRY_BACKEND:-otlp (default)}"
echo "Endpoint: ${AUTOMAGIK_TELEMETRY_ENDPOINT:-default}"
echo "Verbose: ${AUTOMAGIK_TELEMETRY_VERBOSE:-false}"
echo "Environment: ${ENVIRONMENT:-not set}"
echo ""
echo "=== Auto-Disable Detection ==="
echo "CI: ${CI:-not set}"
echo "GitHub Actions: ${GITHUB_ACTIONS:-not set}"
echo ""
echo "=== Opt-Out File ==="
ls -la ~/.automagik-no-telemetry 2>/dev/null && echo "EXISTS (telemetry disabled)" || echo "NOT FOUND (ok)"
```

---

## Common Issues

### 1️⃣ Telemetry Not Sending Data

**Symptoms:**
- No data in backend (ClickHouse/Collector)
- Events tracked but not visible in dashboards
- `get_status()` shows `enabled: false`

<details>
<summary><strong>Solution 1: Enable Telemetry</strong></summary>

**Problem:** Telemetry is disabled by default.

```bash
# Set environment variable
export AUTOMAGIK_TELEMETRY_ENABLED=true

# Verify
echo $AUTOMAGIK_TELEMETRY_ENABLED
```

**Or in code:**

<table>
<tr><th>Python</th><th>TypeScript</th></tr>
<tr>
<td>

```python
telemetry = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)
telemetry.enable()
```

</td>
<td>

```typescript
const telemetry = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});
telemetry.enable();
```

</td>
</tr>
</table>
</details>

<details>
<summary><strong>Solution 2: Check Auto-Disable Environments</strong></summary>

**Problem:** Running in development or CI environment.

```bash
# Check if in auto-disable environment
env | grep -E "^(CI|ENVIRONMENT)="

# Override for testing
export AUTOMAGIK_TELEMETRY_ENABLED=true
export ENVIRONMENT=production
```

**Auto-disable triggers:**
- `ENVIRONMENT=development|dev|test|testing`
- `CI=true`
- `GITHUB_ACTIONS=true`
- File: `~/.automagik-no-telemetry` exists
</details>

<details>
<summary><strong>Solution 3: Remove Opt-Out File</strong></summary>

**Problem:** Opt-out file exists.

```bash
# Check if file exists
ls -la ~/.automagik-no-telemetry

# Remove it
rm ~/.automagik-no-telemetry

# Or use SDK
telemetry.enable()  # Automatically removes file
```
</details>

<details>
<summary><strong>Solution 4: Flush Before Exit</strong></summary>

**Problem:** Application exits before events are sent (when batching enabled).

<table>
<tr><th>Python</th><th>TypeScript</th></tr>
<tr>
<td>

```python
import signal

def cleanup():
    telemetry.flush()  # Force send
    sys.exit(0)

signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

# Or use try-finally
try:
    telemetry.track_event("app.start")
    run_app()
finally:
    telemetry.flush()
```

</td>
<td>

```typescript
process.on('SIGTERM', async () => {
    await telemetry.flush();
    process.exit(0);
});

process.on('SIGINT', async () => {
    await telemetry.flush();
    process.exit(0);
});

// Or use try-finally
try {
    telemetry.trackEvent('app.start');
    await runApp();
} finally {
    await telemetry.flush();
}
```

</td>
</tr>
</table>
</details>

---

### 2️⃣ Connection Timeout / Network Errors

**Symptoms:**
- Timeout errors in logs
- HTTP connection failures
- Events tracked but failing silently

<details>
<summary><strong>Solution 1: Increase Timeout</strong></summary>

**Problem:** Default timeout too short for network conditions.

<table>
<tr><th>Python</th><th>TypeScript</th></tr>
<tr>
<td>

```python
from automagik_telemetry import TelemetryConfig

config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    timeout=30  # 30 seconds (was 5)
)
telemetry = AutomagikTelemetry(config=config)
```

</td>
<td>

```typescript
const telemetry = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    timeout: 30000  // 30 seconds (was 5000)
});
```

</td>
</tr>
</table>

**Or via environment:**
```bash
# Python (seconds)
export AUTOMAGIK_TELEMETRY_TIMEOUT=30

# TypeScript (milliseconds)
export AUTOMAGIK_TELEMETRY_TIMEOUT=30000
```
</details>

<details>
<summary><strong>Solution 2: Verify Endpoint Accessibility</strong></summary>

**Problem:** Endpoint unreachable or incorrect.

```bash
# Test OTLP endpoint
curl -v -X POST https://telemetry.namastex.ai/v1/traces \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Test ClickHouse endpoint
curl -v http://localhost:8123/ping

# Test with timeout
curl --max-time 10 -X POST https://your-endpoint.com/v1/traces
```

**Check firewall/proxy:**
```bash
# Check if endpoint is blocked
nslookup telemetry.namastex.ai
ping telemetry.namastex.ai

# Test from Docker container
docker run --rm curlimages/curl curl https://telemetry.namastex.ai/v1/traces
```
</details>

<details>
<summary><strong>Solution 3: Enable Verbose Logging</strong></summary>

**Problem:** Need to see what's being sent.

```bash
# Enable verbose mode
export AUTOMAGIK_TELEMETRY_VERBOSE=true
```

**Output will show:**
```
[Telemetry] Sending trace
  Endpoint: https://telemetry.namastex.ai/v1/traces
  Size: 1234 bytes (compressed: true)
  Payload preview: {"resourceSpans":[...
```
</details>

---

### 3️⃣ Invalid Configuration Errors

**Symptoms:**
- `ValueError` or `TypeError` on initialization
- "project_name is required" error
- "endpoint must be a valid URL" error

<details>
<summary><strong>Solution 1: Provide Required Fields</strong></summary>

**Problem:** Missing `project_name` or `version`.

**❌ Wrong:**
```python
telemetry = AutomagikTelemetry()  # Missing required fields
```

**✅ Correct:**
```python
telemetry = AutomagikTelemetry(
    project_name="my-app",  # Required
    version="1.0.0"         # Required
)
```
</details>

<details>
<summary><strong>Solution 2: Fix Invalid Endpoint URL</strong></summary>

**Problem:** Endpoint missing protocol or malformed.

**❌ Wrong:**
```python
endpoint="localhost:4318"              # Missing protocol
endpoint="telemetry.example.com"       # Missing protocol
endpoint="ftp://example.com"           # Wrong protocol
```

**✅ Correct:**
```python
endpoint="http://localhost:4318/v1/traces"
endpoint="https://telemetry.example.com/v1/traces"
```

**Validation Rules:**
- Must start with `http://` or `https://`
- Must have valid hostname
- Path is optional but recommended
</details>

<details>
<summary><strong>Solution 3: Fix Type Errors</strong></summary>

**Problem:** Wrong parameter types.

**Common Type Errors:**

| Parameter | Expected | Common Mistake |
|-----------|----------|----------------|
| `timeout` | Python: `int` (seconds)<br>TypeScript: `number` (ms) | `timeout="5"` (string) |
| `batch_size` | `int` | `batch_size="100"` (string) |
| `compression_enabled` | `bool` | `compression_enabled="true"` (string) |

**✅ Correct Types:**
```python
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    timeout=10,              # int (not "10")
    batch_size=100,          # int (not "100")
    compression_enabled=True # bool (not "true")
)
```
</details>

---

### 4️⃣ ClickHouse Backend Issues

**Symptoms:**
- "Connection refused" to ClickHouse
- "Table doesn't exist" errors
- Data not appearing in ClickHouse

<details>
<summary><strong>Solution 1: Verify ClickHouse is Running</strong></summary>

```bash
# Check if ClickHouse is running
curl http://localhost:8123/ping

# Expected output: "Ok."

# Check with credentials
curl -u default: http://localhost:8123/ping

# Check Docker container
docker ps | grep clickhouse
```
</details>

<details>
<summary><strong>Solution 2: Create Required Tables</strong></summary>

**Problem:** Database/table doesn't exist.

```bash
# Check if database exists
curl 'http://localhost:8123/?query=SHOW DATABASES'

# Check if table exists
curl 'http://localhost:8123/?query=SHOW TABLES FROM telemetry'

# Create table (from project root)
cat infra/clickhouse/init-db.sql | \
  curl 'http://localhost:8123/' --data-binary @-
```

**Or manually:**
```sql
CREATE DATABASE IF NOT EXISTS telemetry;

CREATE TABLE IF NOT EXISTS telemetry.traces (
    timestamp DateTime64(9),
    trace_id String,
    span_id String,
    name String,
    attributes Map(String, String),
    -- ... (see infra/clickhouse/init-db.sql for full schema)
) ENGINE = MergeTree()
ORDER BY (timestamp, trace_id);
```
</details>

<details>
<summary><strong>Solution 3: Check Authentication</strong></summary>

**Problem:** Wrong username/password.

```bash
# Test authentication
curl -u username:password http://localhost:8123/ping

# Configure in environment
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME=your_user
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD=your_password
```

**Or in code:**
```python
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    backend="clickhouse",
    clickhouse_username="your_user",
    clickhouse_password="your_password"
)
```
</details>

<details>
<summary><strong>Solution 4: Verify Data Insertion</strong></summary>

```bash
# Check row count
curl 'http://localhost:8123/?query=SELECT COUNT(*) FROM telemetry.traces'

# View recent traces
curl 'http://localhost:8123/?query=SELECT * FROM telemetry.traces ORDER BY timestamp DESC LIMIT 10 FORMAT JSONEachRow'

# Check for specific project
curl 'http://localhost:8123/' --data-binary \
  "SELECT * FROM telemetry.traces WHERE attributes['service.name'] = 'my-app' LIMIT 5 FORMAT JSONEachRow"
```
</details>

---

### 5️⃣ Performance Degradation

**Symptoms:**
- Application slowdown after enabling telemetry
- High CPU usage
- Memory leaks
- Network saturation

<details>
<summary><strong>Solution 1: Enable Batching</strong></summary>

**Problem:** Sending every event immediately (Python default: `batch_size=1`).

**Python - Enable batching:**
```python
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    batch_size=100,        # Send in batches
    flush_interval=5.0     # Auto-flush every 5 seconds
)
```

**TypeScript - Already batched by default:**
```typescript
// TypeScript defaults to batchSize=100
// Increase if needed:
const telemetry = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    batchSize: 500
});
```

**Impact:**
- Reduces network requests by 100x
- Lowers CPU overhead
- Better compression ratios
</details>

<details>
<summary><strong>Solution 2: Enable Compression</strong></summary>

**Problem:** Large payloads consuming bandwidth.

```python
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    compression_enabled=True,      # Enable gzip (default)
    compression_threshold=1024     # Compress payloads > 1KB
)
```

**Impact:**
- 70-80% bandwidth reduction
- Faster transmission
- Minimal CPU overhead
</details>

<details>
<summary><strong>Solution 3: Reduce Retry Attempts</strong></summary>

**Problem:** Too many retries on network failures.

```python
config = TelemetryConfig(
    project_name="my-app",
    version="1.0.0",
    max_retries=1,              # Reduce from 3 to 1
    retry_backoff_base=0.5      # Faster retries
)
```
</details>

<details>
<summary><strong>Solution 4: Sample High-Volume Events</strong></summary>

**Problem:** Too many events overwhelming system.

```python
import random

# Sample 10% of events
if random.random() < 0.1:
    telemetry.track_event("high_frequency_event", data)

# Or sample by user
if hash(user_id) % 10 == 0:  # 10% of users
    telemetry.track_metric("user.action", 1)
```
</details>

---

### 6️⃣ Data Not Appearing in Dashboards

**Symptoms:**
- Events tracked successfully
- No errors in logs
- Data missing from Grafana/visualization

<details>
<summary><strong>Solution 1: Check Data Arrival</strong></summary>

**ClickHouse Backend:**
```bash
# Check if data exists
curl 'http://localhost:8123/?query=SELECT COUNT(*) FROM telemetry.traces'

# View sample data
curl 'http://localhost:8123/' --data-binary \
  "SELECT * FROM telemetry.traces ORDER BY timestamp DESC LIMIT 5 FORMAT Pretty"
```

**OTLP Backend:**
```bash
# Check collector logs
docker logs otel-collector

# Check Prometheus metrics
curl http://localhost:9090/api/v1/query?query=up
```
</details>

<details>
<summary><strong>Solution 2: Verify Time Range</strong></summary>

**Problem:** Grafana looking at wrong time range.

1. Open Grafana dashboard
2. Check time picker (top right)
3. Set to "Last 15 minutes"
4. Click "Refresh"

**Or check timestamps:**
```bash
# Check recent timestamps
curl 'http://localhost:8123/' --data-binary \
  "SELECT timestamp FROM telemetry.traces ORDER BY timestamp DESC LIMIT 1"
```
</details>

<details>
<summary><strong>Solution 3: Check Dashboard Filters</strong></summary>

**Problem:** Filters excluding your data.

1. Check `service.name` filter matches your `project_name`
2. Check environment filter
3. Reset all filters and refresh
</details>

---

## Error Codes

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `project_name is required` | Missing required parameter | Add `project_name` parameter |
| `version is required` | Missing required parameter | Add `version` parameter |
| `endpoint must be a valid URL` | Invalid URL format | Use `http://` or `https://` protocol |
| `timeout must be a positive integer` | Invalid timeout value | Use positive integer (Python: seconds, TypeScript: ms) |
| `Connection refused` | Endpoint not accessible | Check if backend is running, verify firewall |
| `Table doesn't exist` | ClickHouse table missing | Run `infra/clickhouse/init-db.sql` |
| `Authentication failed` | Wrong credentials | Check username/password |
| `HTTP 413 Payload Too Large` | Payload exceeds limit | Enable compression, reduce batch size |
| `HTTP 429 Too Many Requests` | Rate limit exceeded | Reduce event frequency, enable batching |

---

## Backend-Specific Issues

### OTLP Backend

<details>
<summary><strong>Collector Not Receiving Data</strong></summary>

```bash
# Check collector health
curl http://localhost:13133/

# Check collector logs
docker logs otel-collector

# Test endpoint directly
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans":[]}'
```
</details>

<details>
<summary><strong>Prometheus Not Scraping</strong></summary>

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq

# Check if metrics endpoint is accessible
curl http://localhost:8888/metrics

# Verify Prometheus config
cat infra/prometheus/prometheus.yml
```
</details>

---

### ClickHouse Backend

<details>
<summary><strong>High Memory Usage</strong></summary>

**Problem:** ClickHouse consuming too much memory.

```bash
# Check ClickHouse memory usage
docker stats clickhouse

# Optimize table
curl 'http://localhost:8123/' --data-binary \
  "OPTIMIZE TABLE telemetry.traces FINAL"

# Add TTL to auto-delete old data
curl 'http://localhost:8123/' --data-binary \
  "ALTER TABLE telemetry.traces MODIFY TTL timestamp + INTERVAL 30 DAY"
```
</details>

<details>
<summary><strong>Slow Queries</strong></summary>

```bash
# Check query performance
curl 'http://localhost:8123/' --data-binary \
  "SELECT * FROM telemetry.traces WHERE name = 'api.request' FORMAT Null" \
  --header "X-ClickHouse-Debug: 1"

# Add index if needed
curl 'http://localhost:8123/' --data-binary \
  "ALTER TABLE telemetry.traces ADD INDEX name_idx name TYPE bloom_filter GRANULARITY 1"
```
</details>

---

## Performance Issues

### Benchmarking Telemetry Overhead

<table>
<tr><th>Python</th><th>TypeScript</th></tr>
<tr>
<td>

```python
import time

# Measure overhead
iterations = 1000
start = time.time()

for i in range(iterations):
    telemetry.track_event("test", {"i": i})

telemetry.flush()
duration = time.time() - start

print(f"Total: {duration:.2f}s")
print(f"Per event: {duration/iterations*1000:.2f}ms")
```

</td>
<td>

```typescript
// Measure overhead
const iterations = 1000;
const start = performance.now();

for (let i = 0; i < iterations; i++) {
    telemetry.trackEvent('test', { i });
}

await telemetry.flush();
const duration = performance.now() - start;

console.log(`Total: ${duration.toFixed(2)}ms`);
console.log(`Per event: ${(duration/iterations).toFixed(2)}ms`);
```

</td>
</tr>
</table>

**Expected Performance:**
- **Without batching:** 1-5ms per event
- **With batching:** 0.1-0.5ms per event
- **Target:** < 1ms overhead per operation

---

## Debugging Tools

### Enable Debug Logging

<table>
<tr><th>Python</th><th>TypeScript</th></tr>
<tr>
<td>

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Enable verbose telemetry
import os
os.environ["AUTOMAGIK_TELEMETRY_VERBOSE"] = "true"

telemetry = AutomagikTelemetry(
    project_name="debug-test",
    version="1.0.0"
)
```

</td>
<td>

```typescript
// Enable verbose telemetry
process.env.AUTOMAGIK_TELEMETRY_VERBOSE = 'true';

const telemetry = new AutomagikTelemetry({
    projectName: 'debug-test',
    version: '1.0.0'
});
```

</td>
</tr>
</table>

---

### Network Debugging

```bash
# Monitor network traffic
tcpdump -i any -A -s 0 port 8123 or port 4318

# Use mitmproxy to inspect requests
mitmproxy --mode reverse:http://telemetry.namastex.ai@8080

# Then configure SDK to use proxy
export HTTP_PROXY=http://localhost:8080
export HTTPS_PROXY=http://localhost:8080
```

---

### Test Data Generator

<table>
<tr><th>Python</th><th>TypeScript</th></tr>
<tr>
<td>

```python
# Generate test data
for i in range(10):
    telemetry.track_event(f"test.event.{i}", {
        "iteration": i,
        "timestamp": time.time()
    })

telemetry.flush()

# Verify
status = telemetry.get_status()
print(f"Queue sizes: {status['queue_sizes']}")
```

</td>
<td>

```typescript
// Generate test data
for (let i = 0; i < 10; i++) {
    telemetry.trackEvent(`test.event.${i}`, {
        iteration: i,
        timestamp: Date.now()
    });
}

await telemetry.flush();

// Verify
const status = telemetry.getStatus();
console.log('Queue size:', status.queueSize);
```

</td>
</tr>
</table>

---

## 📞 Still Need Help?

### Before Opening an Issue

✅ **Checklist:**
- [ ] Ran [Quick Diagnostics](#quick-diagnostics)
- [ ] Checked [Common Issues](#common-issues)
- [ ] Enabled verbose logging
- [ ] Verified backend is running
- [ ] Tested with minimal configuration
- [ ] Reviewed error logs

### Gather This Information

```bash
# SDK version
pip show automagik-telemetry  # Python
npm list @automagik/telemetry  # TypeScript

# Environment
echo "OS: $(uname -s)"
echo "Python: $(python --version)"  # Python
echo "Node: $(node --version)"      # TypeScript
echo "Environment: $ENVIRONMENT"
echo "Telemetry enabled: $AUTOMAGIK_TELEMETRY_ENABLED"

# Backend info
curl http://localhost:8123/ping  # ClickHouse
docker ps | grep -E "(clickhouse|otel)"  # Containers
```

### Open an Issue

1. Go to: https://github.com/namastexlabs/automagik-telemetry/issues/new
2. Include:
   - SDK version
   - Environment details
   - Error messages (with verbose logging)
   - Minimal reproduction code
   - Steps to reproduce

---

## 📚 Related Documentation

- [API Reference](./API_REFERENCE.md) - Complete API documentation
- [Environment Variables](./ENVIRONMENT_VARIABLES.md) - All environment variables
- [Configuration Reference](../USER_GUIDES/CONFIGURATION.md) - Detailed configuration
- [ClickHouse Backend Guide](../USER_GUIDES/BACKENDS.md) - ClickHouse-specific docs

---

**Built with ❤️ by [Namastex Labs](https://namastex.ai)**
