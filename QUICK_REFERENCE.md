# OpenTelemetry Quick Reference

## 🚀 Quick Start

```bash
# Test telemetry endpoints
python3 test_telemetry_local.py

# View collector logs
ssh root@dl380-g10
pct exec 155 -- journalctl -u otelcol-contrib -f

# Check Prometheus metrics
curl -s "http://192.168.112.122:9090/api/v1/label/__name__/values" | jq
```

## 📡 Endpoints

| Service | URL | Port |
|---------|-----|------|
| **Production HTTPS** | `https://telemetry.namastex.ai` | 443 |
| **Direct HTTP** | `http://192.168.112.155:4318` | 4318 |
| **Direct gRPC** | `http://192.168.112.155:4317` | 4317 |
| **Health Check** | `http://192.168.112.155:13133/health` | 13133 |
| **Prometheus** | `http://192.168.112.122:9090` | 9090 |
| **Grafana** | `http://192.168.112.122:3000` | 3000 |

## 🔧 Python Client Usage

### Current (Traces Only)

```python
from src.core.telemetry import TelemetryClient

client = TelemetryClient()
client.track_api_request(endpoint="/api/v1/runs", method="POST")
client.track_feature(feature_name="runs", category="api_endpoint")
```

### With Metrics (To Implement)

```python
# Counter - for things that only go up
client.track_counter("api.requests", value=1, attributes={
    "endpoint": "/api/v1/runs",
    "method": "POST",
    "status": 200
})

# Gauge - for things that go up and down
client.track_gauge("system.memory_usage_mb", value=512.5, attributes={
    "host": "server-01"
})

# Histogram - for distributions
client.track_histogram("api.response_time_ms", value=125.3, attributes={
    "endpoint": "/api/v1/runs"
})
```

## 🧪 Testing

### Send Test Data

```bash
python3 test_telemetry_local.py
```

### Check if Data Arrived

```bash
# Wait 15-30 seconds for batch processing, then:
curl -s "http://192.168.112.122:9090/api/v1/label/__name__/values" | jq -r '.data[]'
```

### Query Specific Metric

```bash
curl -s 'http://192.168.112.122:9090/api/v1/query?query=test_api_requests_total' | jq
```

### Query with Labels

```bash
curl -s 'http://192.168.112.122:9090/api/v1/query?query=api_requests_total{method="POST"}' | jq
```

## 🐛 Debugging

### Check Collector Status

```bash
ssh root@dl380-g10
pct exec 155 -- systemctl status otelcol-contrib
```

### View Live Logs

```bash
pct exec 155 -- journalctl -u otelcol-contrib -f
```

### Search for Errors

```bash
pct exec 155 -- journalctl -u otelcol-contrib -n 200 --no-pager | grep -i error
```

### Test Health Endpoint

```bash
curl http://192.168.112.155:13133/health
# or
curl https://telemetry.namastex.ai/health
```

### Verify Endpoints

```bash
# Should return 405 (Method Not Allowed) - that's normal
curl -X GET https://telemetry.namastex.ai/v1/traces
curl -X GET https://telemetry.namastex.ai/v1/metrics

# Should return 200 with empty payload
curl -X POST https://telemetry.namastex.ai/v1/traces \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans":[]}'
```

## 📊 Prometheus Queries

### List All Metrics

```bash
curl -s "http://192.168.112.122:9090/api/v1/label/__name__/values" | jq -r '.data[]'
```

### Query Counter

```bash
curl -s 'http://192.168.112.122:9090/api/v1/query?query=api_requests_total' | jq
```

### Query with Time Range

```bash
curl -s 'http://192.168.112.122:9090/api/v1/query_range?query=api_requests_total&start=2025-10-21T00:00:00Z&end=2025-10-21T23:59:59Z&step=1h' | jq
```

### Aggregate by Label

```bash
curl -s 'http://192.168.112.122:9090/api/v1/query?query=sum(api_requests_total)by(endpoint)' | jq
```

## 🎯 Common Patterns

### API Request Instrumentation

```python
@app.post("/api/v1/runs")
async def create_run():
    start_time = time.time()

    try:
        result = await process_run()

        # Track success
        client.track_counter("api.requests", attributes={
            "endpoint": "/api/v1/runs",
            "method": "POST",
            "status": 200
        })

        return result

    except Exception as e:
        # Track error
        client.track_counter("api.requests", attributes={
            "endpoint": "/api/v1/runs",
            "method": "POST",
            "status": 500,
            "error": type(e).__name__
        })
        raise

    finally:
        # Track response time
        duration_ms = (time.time() - start_time) * 1000
        client.track_histogram("api.response_time_ms", value=duration_ms, attributes={
            "endpoint": "/api/v1/runs"
        })
```

### Business Metrics

```python
# Track feature usage
client.track_counter("feature.used", attributes={
    "feature": "agent_runs",
    "user_tier": "premium"
})

# Track resource usage
client.track_gauge("system.active_connections", value=len(connections))
client.track_gauge("queue.depth", value=queue.size())

# Track processing metrics
client.track_histogram("job.duration_seconds", value=duration, attributes={
    "job_type": "data_processing"
})
```

## 🚨 Troubleshooting

### No Metrics Appearing in Prometheus

**Check:**
1. Is collector receiving data? `pct exec 155 -- journalctl -u otelcol-contrib -f | grep metric`
2. Is Prometheus remote write configured? `pct exec 155 -- cat /etc/otelcol-contrib/config.yaml | grep prometheusremotewrite`
3. Wait 15-30 seconds for batch processing

### Connection Refused

**Check:**
1. Collector running? `pct exec 155 -- systemctl status otelcol-contrib`
2. Ports open? `pct exec 155 -- ss -tulpn | grep -E "4317|4318"`
3. Using correct endpoint? Production: `https://telemetry.namastex.ai`, Local: `http://192.168.112.155:4318`

### High Latency

**Solution:** Ensure you're using async sending (already implemented in TelemetryClient)

## 📚 More Information

See `TELEMETRY_DEVELOPMENT_GUIDE.md` for:
- Complete architecture overview
- Detailed implementation guide
- Adding metrics support to TelemetryClient
- Grafana dashboard setup
- Performance considerations

## 🔐 Environment Variables

```bash
# Disable telemetry
export AUTOMAGIK_OMNI_DISABLE_TELEMETRY=true

# Custom endpoint (if needed)
export OTEL_EXPORTER_OTLP_ENDPOINT="https://telemetry.namastex.ai"

# Development mode (auto-disables telemetry)
export ENVIRONMENT=development
```

## 📦 Files

- `TELEMETRY_DEVELOPMENT_GUIDE.md` - Complete developer guide
- `test_telemetry_local.py` - Python test script
- `test_telemetry_health.sh` - Bash test script
- `view_telemetry_logs.sh` - View collector logs
- `QUICK_REFERENCE.md` - This file

---

**Need Help?** Check collector logs first, then verify endpoints are reachable!
