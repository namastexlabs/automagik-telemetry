# ⚡ Quick Reference

> *Fast command reference and cheat sheet for Automagik Telemetry*

<p align="center">
  <strong>🎯 Everything you need at your fingertips</strong><br>
  Commands, patterns, and common recipes
</p>

---

## 📑 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [📡 Endpoints](#-endpoints)
- [🔧 SDK Usage](#-sdk-usage)
- [🧪 Testing](#-testing)
- [📊 Queries](#-queries)
- [🐛 Debugging](#-debugging)
- [🎯 Common Patterns](#-common-patterns)
- [🔐 Environment Variables](#-environment-variables)

---

## 🚀 Quick Start

<details open>
<summary><strong>💡 Essential Commands</strong></summary>

```bash
# 🏗️ Infrastructure Management
cd infra && make start          # Start all services
make stop                        # Stop all services
make restart                     # Restart services
make status                      # Check status

# 🧪 Testing
make test                        # Send test data
make dashboard                   # Open Grafana

# 📊 Data Queries
make query-traces                # Show recent traces
make query-stats                 # Show statistics

# 🔍 Debugging
make logs                        # View all logs
make logs-clickhouse             # ClickHouse logs only
make logs-collector              # Collector logs only
make logs-grafana                # Grafana logs only
make health                      # Health check
```

</details>

---

## 📡 Endpoints

<table>
<tr>
<th>Service</th>
<th>URL</th>
<th>Port</th>
<th>Purpose</th>
</tr>
<tr>
<td>☁️ <strong>Production</strong></td>
<td><code>https://telemetry.namastex.ai</code></td>
<td>443</td>
<td>OTLP Production endpoint</td>
</tr>
<tr>
<td>📡 <strong>Local OTLP HTTP</strong></td>
<td><code>http://localhost:4318</code></td>
<td>4318</td>
<td>Local OTLP HTTP endpoint</td>
</tr>
<tr>
<td>📡 <strong>Local OTLP gRPC</strong></td>
<td><code>http://localhost:4317</code></td>
<td>4317</td>
<td>Local OTLP gRPC endpoint</td>
</tr>
<tr>
<td>🗄️ <strong>ClickHouse HTTP</strong></td>
<td><code>http://localhost:8123</code></td>
<td>8123</td>
<td>ClickHouse HTTP API</td>
</tr>
<tr>
<td>🗄️ <strong>ClickHouse Native</strong></td>
<td><code>http://localhost:9000</code></td>
<td>9000</td>
<td>ClickHouse Native protocol</td>
</tr>
<tr>
<td>📊 <strong>Grafana</strong></td>
<td><code>http://localhost:3000</code></td>
<td>3000</td>
<td>Visualization dashboards</td>
</tr>
<tr>
<td>💚 <strong>Health Check</strong></td>
<td><code>http://localhost:13133/health</code></td>
<td>13133</td>
<td>Collector health endpoint</td>
</tr>
</table>

---

## 🔧 SDK Usage

### 🐍 Python Client

<details>
<summary><strong>📝 Events (Traces)</strong></summary>

```python
from automagik_telemetry import AutomagikTelemetry

# Initialize
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# Track event
client.track_event("api.request", {
    "endpoint": "/api/v1/runs",
    "method": "POST",
    "status": 200
})

# Track error
try:
    risky_operation()
except Exception as e:
    client.track_error(e, {
        "context": "payment_processing",
        "user_tier": "premium"
    })
```

</details>

<details>
<summary><strong>📊 Metrics</strong></summary>

```python
from automagik_telemetry import AutomagikTelemetry, MetricType

client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# 📈 Counter - Monotonically increasing
client.track_metric(
    "api.requests",
    value=1,
    metric_type=MetricType.COUNTER,
    attributes={
        "endpoint": "/api/v1/runs",
        "method": "POST",
        "status": 200
    }
)

# 📊 Gauge - Up and down values
client.track_metric(
    "system.memory_usage_mb",
    value=512.5,
    metric_type=MetricType.GAUGE,
    attributes={"host": "server-01"}
)

# 📉 Histogram - Value distributions
client.track_metric(
    "api.response_time_ms",
    value=125.3,
    metric_type=MetricType.HISTOGRAM,
    attributes={"endpoint": "/api/v1/runs"}
)
```

</details>

<details>
<summary><strong>📝 Logs (Structured Logging)</strong></summary>

```python
from automagik_telemetry import AutomagikTelemetry, LogSeverity

client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
)

# 📘 INFO - Informational messages (default)
client.track_log("Application started successfully", LogSeverity.INFO)

# ⚠️ WARN - Warning conditions
client.track_log("Cache miss rate high", LogSeverity.WARN, {
    "cache_hit_rate": 0.45,
    "threshold": 0.80
})

# ❌ ERROR - Error events
client.track_log("Database connection failed", LogSeverity.ERROR, {
    "error": "connection_timeout",
    "retry_count": 3
})

# 🔥 FATAL - Critical errors
client.track_log("System memory exhausted", LogSeverity.FATAL, {
    "available_mb": 50,
    "required_mb": 512
})

# 🔍 DEBUG - Debugging information
client.track_log("Cache operation details", LogSeverity.DEBUG, {
    "operation": "get",
    "key": "user_session_123",
    "hit": True
})

# 🔬 TRACE - Finest detail
client.track_log("Method entry", LogSeverity.TRACE, {
    "method": "processPayment",
    "args": {"amount": 99.99}
})
```

**Log Severity Levels:**
- `TRACE` (1) - Finest granularity, debugging
- `DEBUG` (5) - Detailed debugging information
- `INFO` (9) - Informational messages (default)
- `WARN` (13) - Warning conditions
- `ERROR` (17) - Error events
- `FATAL` (21) - Critical errors

</details>

<details>
<summary><strong>⚙️ Configuration</strong></summary>

```python
from automagik_telemetry import AutomagikTelemetry

# OTLP Backend (Default)
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    endpoint="http://localhost:4318/v1/traces"
)

# ClickHouse Backend (Direct)
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    backend="clickhouse",
    clickhouse_endpoint="http://localhost:8123",
    clickhouse_database="telemetry",
    clickhouse_username="telemetry",
    clickhouse_password="telemetry_password"
)
```

</details>

---

### 📘 TypeScript Client

<details>
<summary><strong>📝 Events & Metrics</strong></summary>

```typescript
import { AutomagikTelemetry, MetricType } from 'automagik-telemetry';

// Initialize
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// Track event
client.trackEvent('api.request', {
    endpoint: '/api/v1/runs',
    method: 'POST',
    status: 200
});

// Track metric
client.trackMetric(
    'api.requests',
    1,
    MetricType.COUNTER,
    { endpoint: '/api/v1/runs', status: 200 }
);

// Track error
try {
    await riskyOperation();
} catch (error) {
    client.trackError(error, {
        context: 'payment_processing'
    });
}
```

</details>

<details>
<summary><strong>📝 Logs (Structured Logging)</strong></summary>

```typescript
import { AutomagikTelemetry, LogSeverity } from 'automagik-telemetry';

const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0'
});

// 📘 INFO - Informational messages (default)
client.trackLog('Application started successfully', LogSeverity.INFO);

// ⚠️ WARN - Warning conditions
client.trackLog('Cache miss rate high', LogSeverity.WARN, {
    cache_hit_rate: 0.45,
    threshold: 0.80
});

// ❌ ERROR - Error events
client.trackLog('Database connection failed', LogSeverity.ERROR, {
    error: 'connection_timeout',
    retry_count: 3
});

// 🔥 FATAL - Critical errors
client.trackLog('System memory exhausted', LogSeverity.FATAL, {
    available_mb: 50,
    required_mb: 512
});

// 🔍 DEBUG - Debugging information
client.trackLog('Cache operation details', LogSeverity.DEBUG, {
    operation: 'get',
    key: 'user_session_123',
    hit: true
});

// 🔬 TRACE - Finest detail
client.trackLog('Method entry', LogSeverity.TRACE, {
    method: 'processPayment',
    args: { amount: 99.99 }
});
```

**Log Severity Levels:**
- `TRACE` (1) - Finest granularity, debugging
- `DEBUG` (5) - Detailed debugging information
- `INFO` (9) - Informational messages (default)
- `WARN` (13) - Warning conditions
- `ERROR` (17) - Error events
- `FATAL` (21) - Critical errors

</details>

<details>
<summary><strong>⚙️ Configuration</strong></summary>

```typescript
import { AutomagikTelemetry } from 'automagik-telemetry';

// OTLP Backend
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    endpoint: 'http://localhost:4318/v1/traces'
});

// ClickHouse Backend
const client = new AutomagikTelemetry({
    projectName: 'my-app',
    version: '1.0.0',
    backend: 'clickhouse',
    clickhouseEndpoint: 'http://localhost:8123',
    clickhouseDatabase: 'telemetry',
    clickhouseUsername: 'telemetry',
    clickhousePassword: 'telemetry_password'
});
```

</details>

---

## 🧪 Testing

### Send Test Data

<details>
<summary><strong>📦 Test Commands</strong></summary>

```bash
# Using Make
cd infra && make test

# Manual Python test
python3 test_telemetry_local.py

# Manual cURL test (OTLP)
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans":[]}'

# Manual ClickHouse test
curl -u telemetry:telemetry_password \
  -X POST "http://localhost:8123/?query=INSERT%20INTO%20telemetry.traces%20FORMAT%20JSONEachRow" \
  -d '{"trace_id":"test123","span_id":"span123","timestamp":"2025-10-22 00:00:00"}'
```

</details>

### Verify Data Arrival

<details>
<summary><strong>✅ Verification Commands</strong></summary>

```bash
# Query ClickHouse
curl "http://localhost:8123/?query=SELECT%20count()%20FROM%20telemetry.traces"

# Using clickhouse-client
clickhouse-client --host localhost --port 9000 \
  --query="SELECT count() FROM telemetry.traces"

# View recent traces
make query-traces

# View statistics
make query-stats
```

</details>

---

## 📊 Queries

### ClickHouse Queries

<details>
<summary><strong>🔍 Common Queries</strong></summary>

**Recent traces:**
```sql
SELECT
    timestamp,
    project_name,
    span_name,
    status_code,
    duration_ms
FROM telemetry.traces
ORDER BY timestamp DESC
LIMIT 10
```

**Events by project:**
```sql
SELECT
    project_name,
    count() as events,
    avg(duration_ms) as avg_duration
FROM telemetry.traces
WHERE timestamp > now() - INTERVAL 1 HOUR
GROUP BY project_name
ORDER BY events DESC
```

**Error rate:**
```sql
SELECT
    toStartOfHour(timestamp) as hour,
    countIf(status_code = 'ERROR') / count() * 100 as error_rate
FROM telemetry.traces
WHERE timestamp > now() - INTERVAL 24 HOUR
GROUP BY hour
ORDER BY hour
```

**Top slow endpoints:**
```sql
SELECT
    span_name,
    count() as requests,
    avg(duration_ms) as avg_ms,
    max(duration_ms) as max_ms,
    quantile(0.95)(duration_ms) as p95_ms
FROM telemetry.traces
WHERE timestamp > now() - INTERVAL 1 HOUR
GROUP BY span_name
HAVING requests > 10
ORDER BY p95_ms DESC
LIMIT 10
```

</details>

---

## 🐛 Debugging

### Health Checks

<details>
<summary><strong>💚 Service Health</strong></summary>

```bash
# All services
make health

# ClickHouse
curl http://localhost:8123/ping
# Should return: Ok.

# OTLP Collector
curl http://localhost:13133/health
# Should return: {"status":"Server available","upSince":...}

# Grafana
curl http://localhost:3000/api/health
# Should return: {"database":"ok","version":...}
```

</details>

### View Logs

<details>
<summary><strong>📋 Log Commands</strong></summary>

```bash
# All services
make logs

# Specific service
make logs-clickhouse
make logs-collector
make logs-grafana

# Follow logs (live)
docker logs -f automagik-clickhouse
docker logs -f automagik-collector
docker logs -f automagik-grafana

# Search for errors
docker logs automagik-collector 2>&1 | grep -i error
```

</details>

### Common Issues

<details>
<summary><strong>🚨 Troubleshooting Guide</strong></summary>

| Issue | Check | Solution |
|-------|-------|----------|
| 🔴 **Connection Refused** | Service running? | `make status` → `make start` |
| 📭 **No Data** | Data being sent? | `make test` → `make query-traces` |
| 🔒 **Auth Failed** | Credentials correct? | Check `.env` file or config |
| 💾 **Table Missing** | Database initialized? | `make restart` (re-runs init script) |
| ⏱️ **High Latency** | Batch size optimal? | Increase `batch_size` in config |

</details>

---

## 🎯 Common Patterns

### API Instrumentation

<details>
<summary><strong>📡 REST API Tracking</strong></summary>

```python
import time
from automagik_telemetry import MetricType

@app.post("/api/v1/runs")
async def create_run():
    start_time = time.time()

    try:
        result = await process_run()

        # ✅ Track success
        client.track_metric("api.requests", 1, MetricType.COUNTER, {
            "endpoint": "/api/v1/runs",
            "method": "POST",
            "status": 200
        })

        return result

    except Exception as e:
        # ❌ Track error
        client.track_metric("api.requests", 1, MetricType.COUNTER, {
            "endpoint": "/api/v1/runs",
            "method": "POST",
            "status": 500,
            "error": type(e).__name__
        })
        raise

    finally:
        # ⏱️ Track response time
        duration_ms = (time.time() - start_time) * 1000
        client.track_metric("api.response_time_ms", duration_ms, MetricType.HISTOGRAM, {
            "endpoint": "/api/v1/runs"
        })
```

</details>

### Business Metrics

<details>
<summary><strong>📊 Feature Usage Tracking</strong></summary>

```python
from automagik_telemetry import MetricType

# 🎯 Feature usage
client.track_metric("feature.used", 1, MetricType.COUNTER, {
    "feature": "agent_runs",
    "user_tier": "premium"
})

# 💰 Revenue tracking
client.track_metric("revenue.earned", 99.99, MetricType.COUNTER, {
    "plan": "enterprise",
    "currency": "USD"
})

# 👥 Active users
client.track_metric("users.active", len(active_users), MetricType.GAUGE)

# 📦 Queue depth
client.track_metric("queue.depth", queue.size(), MetricType.GAUGE, {
    "queue_name": "background_jobs"
})

# ⏱️ Job duration
client.track_metric("job.duration_seconds", duration, MetricType.HISTOGRAM, {
    "job_type": "data_processing"
})
```

</details>

---

## 🔐 Environment Variables

<details open>
<summary><strong>⚙️ Configuration Variables</strong></summary>

```bash
# 🎯 Telemetry Control
export AUTOMAGIK_TELEMETRY_ENABLED=true
export AUTOMAGIK_TELEMETRY_VERBOSE=true  # Debug mode

# 🔌 Backend Selection
export AUTOMAGIK_TELEMETRY_BACKEND=otlp  # or "clickhouse"

# 📡 OTLP Configuration
export AUTOMAGIK_TELEMETRY_ENDPOINT=https://telemetry.namastex.ai/v1/traces
export AUTOMAGIK_TELEMETRY_TIMEOUT=5000

# 🗄️ ClickHouse Configuration
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://localhost:8123
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE=telemetry
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME=telemetry
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD=telemetry_password
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_BATCH_SIZE=100

# 🔒 Privacy
export ENVIRONMENT=development  # Auto-disables telemetry
touch ~/.automagik-no-telemetry  # Permanent opt-out
```

</details>

---

## 📚 Cheat Sheets

### Metric Types

<table>
<tr>
<th>Type</th>
<th>When to Use</th>
<th>Example</th>
</tr>
<tr>
<td>📈 <strong>COUNTER</strong></td>
<td>Values that only go up</td>
<td>Requests, errors, revenue</td>
</tr>
<tr>
<td>📊 <strong>GAUGE</strong></td>
<td>Values that go up and down</td>
<td>Memory usage, active connections, queue depth</td>
</tr>
<tr>
<td>📉 <strong>HISTOGRAM</strong></td>
<td>Value distributions</td>
<td>Response times, file sizes, durations</td>
</tr>
</table>

### Status Codes

| Code | Meaning | When to Use |
|------|---------|-------------|
| `OK` | Success | Operation completed successfully |
| `ERROR` | Failure | Operation failed |
| `UNSET` | Unknown | Status not determined |

---

## 🔗 Related Documentation

- ⚙️ [CONFIGURATION.md](./CONFIGURATION.md) - Complete configuration guide
- 🔌 [BACKENDS.md](./BACKENDS.md) - Backend setup and comparison
- 🔒 [PRIVACY.md](./PRIVACY.md) - Privacy policy and data handling
- 🏗️ [SELF_HOSTING.md](./SELF_HOSTING.md) - Infrastructure deployment guide

---

## 🆘 Quick Help

<details>
<summary><strong>💬 Need Help?</strong></summary>

**Before asking:**
1. ✅ Check service status: `make status`
2. 📋 View logs: `make logs`
3. 🧪 Try test command: `make test`
4. 💚 Verify health: `make health`

**Get Support:**
- **GitHub Issues**: [github.com/namastexlabs/automagik-telemetry/issues](https://github.com/namastexlabs/automagik-telemetry/issues)
- **Discord**: [discord.gg/xcW8c7fF3R](https://discord.gg/xcW8c7fF3R)
- **Documentation**: [DeepWiki](https://deepwiki.com/namastexlabs/automagik-telemetry)

</details>

---

<p align="center">
  <strong>Built with ❤️ by <a href="https://namastex.ai">Namastex Labs</a></strong><br>
  <em>Quick reference for fast development</em>
</p>
